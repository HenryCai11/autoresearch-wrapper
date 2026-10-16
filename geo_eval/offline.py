"""Site-wide technical checks: is the site machine-readable at all?

Per-keyword coverage lives in the eval matrix (geo_eval.matrix); these checks
cover what applies to the site as a whole. Each returns a value in [0, 1];
the technical score is their weighted mean on 0-100.

Guardrails are separate: they flag ways to game a score (hidden text, padding)
and make the caller treat the candidate as a failure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .kmap import KnowledgeMap, contains_any, contains_term, normalize
from .site import Page, Site

AI_CRAWLERS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"]

WEIGHTS = {"structured_data": 0.35, "crawler_files": 0.25, "metadata": 0.25, "hygiene": 0.15}
# Metric v2 adds scholarly checks: per-paper pages, Google Scholar tags, front-loaded identity.
WEIGHTS_V2 = {"structured_data": 0.25, "crawler_files": 0.2, "metadata": 0.2, "hygiene": 0.1, "scholarly": 0.25}
FRONT_CHARS = 600


@dataclass
class Check:
    name: str
    category: str
    value: float
    detail: str = ""


@dataclass
class TechnicalResult:
    score: float
    categories: dict[str, float]
    checks: list[Check]
    guardrail_violations: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "categories": self.categories,
            "checks": [check.__dict__ for check in self.checks],
            "guardrail_violations": self.guardrail_violations,
            "stats": self.stats,
        }


def score_technical(site: Site, kmap: KnowledgeMap, version: int = 1) -> TechnicalResult:
    home = site.home or Page(path="/")
    checks: list[Check] = []
    checks += _structured_data_checks(site, kmap)
    checks += _crawler_file_checks(site, kmap)
    checks += _metadata_checks(home, kmap)
    checks += _hygiene_checks(site, home, kmap)
    weights = WEIGHTS
    if version >= 2:
        checks += _scholarly_checks(site, home, kmap)
        weights = WEIGHTS_V2

    categories: dict[str, float] = {}
    for category in weights:
        values = [check.value for check in checks if check.category == category]
        categories[category] = round(sum(values) / len(values), 4) if values else 0.0
    return TechnicalResult(
        score=round(100 * sum(weights[c] * v for c, v in categories.items()), 2),
        categories=categories,
        checks=checks,
        guardrail_violations=guardrails(site, kmap),
        stats={
            "pages": len(site.pages),
            "home_visible_chars": len(home.visible_text),
            "site_visible_chars": len(site.all_visible_text()),
        },
    )


def json_ld_types(item: dict) -> set[str]:
    value = item.get("@type", [])
    return set(value if isinstance(value, list) else [value])


def find_person(site: Site, kmap: KnowledgeMap) -> dict | None:
    return next(
        (
            item
            for item in site.all_json_ld()
            if "Person" in json_ld_types(item) and contains_term(str(item.get("name", "")), kmap.name)
        ),
        None,
    )


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else ([value] if value else [])


def _structured_data_checks(site: Site, kmap: KnowledgeMap) -> list[Check]:
    errors = sum(page.json_ld_errors for page in site.pages.values())
    person = find_person(site, kmap)
    checks = [
        Check("person_jsonld", "structured_data", 1.0 if person else 0.0, "JSON-LD Person for the entity"),
        Check("jsonld_valid", "structured_data", 0.0 if errors else 1.0, f"{errors} unparseable JSON-LD blocks"),
    ]
    if person:
        same_as = _as_list(person.get("sameAs"))
        checks += [
            Check(
                "person_alias",
                "structured_data",
                1.0 if contains_any(" ".join(map(str, _as_list(person.get("alternateName")))), kmap.aliases or [kmap.name]) else 0.0,
                "alternateName lists an alias",
            ),
            Check("person_same_as", "structured_data", min(len(same_as), 3) / 3, f"{len(same_as)} sameAs profile links"),
            Check("person_url", "structured_data", 1.0 if person.get("url") else 0.0, "url"),
        ]
    if kmap.papers():
        articles = [item for item in site.all_json_ld() if json_ld_types(item) & {"ScholarlyArticle", "Article"}]
        checks.append(Check("papers_typed", "structured_data", 1.0 if articles else 0.0, f"{len(articles)} ScholarlyArticle records"))
    return checks


def _crawler_file_checks(site: Site, kmap: KnowledgeMap) -> list[Check]:
    checks = [Check("llms_txt", "crawler_files", 1.0 if site.llms_txt and contains_term(site.llms_txt, kmap.name) else 0.0, "llms.txt naming the entity")]
    robots = site.robots_txt
    if robots is None:
        checks.append(Check("robots_allows_ai", "crawler_files", 1.0, "no robots.txt (all crawlers allowed)"))
        checks.append(Check("robots_sitemap", "crawler_files", 0.0, "no robots.txt pointing at the sitemap"))
    else:
        blocked = [bot for bot in AI_CRAWLERS if robots_blocks(robots, bot)]
        checks.append(Check("robots_allows_ai", "crawler_files", 1 - len(blocked) / len(AI_CRAWLERS), f"blocked: {blocked or 'none'}"))
        checks.append(Check("robots_sitemap", "crawler_files", 1.0 if re.search(r"(?im)^\s*sitemap\s*:", robots) else 0.0, "Sitemap: line"))
    checks.append(Check("sitemap_xml", "crawler_files", 1.0 if site.sitemap_xml and "<loc>" in site.sitemap_xml else 0.0, "sitemap.xml with URLs"))
    return checks


def robots_blocks(robots: str, bot: str) -> bool:
    """True if the group for `bot` (falling back to `*`) disallows the whole site."""
    groups: list[tuple[set[str], list[str]]] = []
    agents: set[str] = set()
    rules: list[str] = []
    for line in robots.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = set(), []
            agents.add(value.lower())
        elif key in ("disallow", "allow"):
            rules.append(f"{key}:{value}")
    if agents:
        groups.append((agents, rules))
    specific = [rules for agents, rules in groups if bot.lower() in agents]
    chosen = specific[0] if specific else next((rules for agents, rules in groups if "*" in agents), [])
    return "disallow:/" in chosen and "allow:/" not in chosen


def _metadata_checks(home: Page, kmap: KnowledgeMap) -> list[Check]:
    description = home.meta.get("description", "")
    hop0_terms = [term for node in kmap.by_hop(0) for term in node.terms]
    return [
        Check("title_names_entity", "metadata", 1.0 if contains_term(home.title, kmap.name) else 0.0, home.title[:80]),
        Check(
            "meta_description",
            "metadata",
            (0.4 if 50 <= len(description) <= 300 else 0.0)
            + (0.3 if contains_term(description, kmap.name) else 0.0)
            + (0.3 if contains_any(description, hop0_terms) else 0.0),
            description[:120] or "missing",
        ),
        Check("canonical", "metadata", 1.0 if home.canonical else 0.0, home.canonical or "missing"),
        Check(
            "open_graph",
            "metadata",
            (0.5 if home.meta.get("og:title") else 0.0) + (0.5 if home.meta.get("og:description") else 0.0),
            "og:title / og:description",
        ),
    ]


def _scholarly_checks(site: Site, home: Page, kmap: KnowledgeMap) -> list[Check]:
    """Metric v2: what lets scholarly search and answer engines index and attribute work."""
    checks = []
    papers = kmap.papers()
    if papers:
        subpages = [page for path, page in site.pages.items() if path != "/"]
        with_page = [p.id for p in papers if any(contains_any(page.title, p.terms) for page in subpages)]
        checks.append(Check("paper_pages", "scholarly", len(with_page) / len(papers), f"{len(with_page)}/{len(papers)} papers have their own page"))
        tagged = [
            p.id
            for p in papers
            if any(
                contains_any(page.meta.get("citation_title", ""), p.terms) and page.meta.get("citation_author")
                for page in site.pages.values()
            )
        ]
        checks.append(Check("scholar_meta", "scholarly", len(tagged) / len(papers), f"{len(tagged)}/{len(papers)} papers with citation_title + citation_author tags"))
        listed = [p.id for p in papers if site.llms_txt and contains_any(site.llms_txt, p.terms)]
        checks.append(Check("llms_lists_papers", "scholarly", len(listed) / len(papers), f"{len(listed)}/{len(papers)} papers in llms.txt"))
    hop0 = kmap.by_hop(0)
    if hop0:
        front = home.visible_text[:FRONT_CHARS]
        early = [node.id for node in hop0 if contains_any(front, node.terms)]
        checks.append(Check("identity_front_loaded", "scholarly", len(early) / len(hop0), f"{len(early)}/{len(hop0)} core facts in the first {FRONT_CHARS} chars"))
    if kmap.aliases:
        shown = [alias for alias in kmap.aliases if contains_term(home.visible_text, alias)]
        checks.append(Check("aliases_visible", "scholarly", len(shown) / len(kmap.aliases), f"visible aliases: {shown or 'none'}"))
    return checks


def _hygiene_checks(site: Site, home: Page, kmap: KnowledgeMap) -> list[Check]:
    checks = []
    if kmap.forbidden:
        text = normalize(
            site.all_visible_text()
            + " "
            + " ".join(page.title + " " + page.meta.get("description", "") for page in site.pages.values())
        )
        hits = [item["text"] for item in kmap.forbidden if normalize(item["text"]) in text]
        checks.append(Check("no_forbidden_text", "hygiene", 1 - len(hits) / len(kmap.forbidden), f"present: {hits or 'none'}"))
    if home.images:
        checks.append(Check("image_alt", "hygiene", home.images_with_alt / home.images, f"{home.images_with_alt}/{home.images} images with alt"))
    return checks or [Check("hygiene", "hygiene", 1.0, "nothing to check")]


def guardrails(site: Site, kmap: KnowledgeMap) -> list[str]:
    """Ways a candidate could game a score; any violation should fail it."""
    violations = []
    # Themes legitimately hide duplicates (mobile menus, sidebars). Stuffing is a map
    # term that a reader can only find in hidden text.
    hidden = " ".join(page.hidden_text for page in site.pages.values())
    visible = site.all_visible_text()
    stuffed = [
        term
        for node in kmap.nodes
        for term in node.terms
        if contains_term(hidden, term) and not contains_term(visible, term)
    ]
    if stuffed:
        violations.append(f"map terms only in hidden text: {stuffed[:5]}")
    limit = kmap.limits.get("max_visible_chars")
    home = site.home
    if limit and home and len(home.visible_text) > int(limit):
        violations.append(f"homepage visible text {len(home.visible_text)} chars exceeds limit {limit}")
    return violations
