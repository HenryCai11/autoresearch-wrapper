"""GEO site graph, scoped edits, and honest cross-platform evaluation.

This module deliberately separates local readiness from observed search exposure.
Search results and answer citations are supplied by independent observations.
"""

from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


METRIC_WEIGHTS = {
    "project_rank": 0.30,
    "project_cited": 0.35,
    "target_mentioned": 0.15,
    "paper_rank": 0.10,
    "answer_accurate": 0.10,
}


class SectionParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.stack: list[tuple[str | None, int]] = []
        self.sections: dict[str, tuple[int, int]] = {}
        self.references: list[tuple[str, str]] = []

    def absolute_offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "section":
            self.stack.append((values.get("id"), self.absolute_offset()))
        for attribute in ("href", "src"):
            if values.get(attribute):
                self.references.append((attribute, values[attribute] or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag != "section" or not self.stack:
            return
        section_id, start = self.stack.pop()
        if section_id:
            end = self.source.find(">", self.absolute_offset()) + 1
            self.sections[section_id] = (start, end)


def read_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    platforms = data.get("platforms", {})
    if not platforms or any(float(weight) <= 0 for weight in platforms.values()):
        raise ValueError("config needs positive platform weights")
    if not data.get("site_url") or not data.get("paper_url"):
        raise ValueError("config needs site_url and paper_url")
    return data


def _add(nodes: dict[str, dict[str, Any]], node_id: str, kind: str, *, path: str | None = None,
         mutable: bool = False, operations: list[str] | None = None, **details: Any) -> None:
    nodes[node_id] = {"id": node_id, "kind": kind, "path": path, "mutable": mutable,
                      "operations": operations or [], **details}


def build_graph(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    files = ["index.html", "README.md", "robots.txt", "sitemap.xml", "styles.css",
             "script.js", "site-config.js"]
    for name in files:
        if (repo / name).is_file():
            _add(nodes, f"file:{name}", "file", path=name, mutable=True,
                 operations=["replace_text"])
    home = (repo / "index.html").read_text(encoding="utf-8") if (repo / "index.html").is_file() else ""
    parser = SectionParser(home)
    parser.feed(home)
    for section_id, (start, end) in sorted(parser.sections.items()):
        node_id = f"section:{section_id}"
        _add(nodes, node_id, "html-section", path="index.html", mutable=True,
             operations=["add_after", "edit", "move_after", "remove"],
             span=[start, end])
        edges.add(("file:index.html", node_id, "contains"))
    for name, pattern in {
        "title": r"<title\b[^>]*>.*?</title>",
        "description": r'<meta\s+name=["\']description["\'][^>]*>',
        "canonical": r'<link\s+rel=["\']canonical["\'][^>]*>',
        "schema": r'<script\s+type=["\']application/ld\+json["\'][^>]*>.*?</script>',
    }.items():
        match = re.search(pattern, home, re.IGNORECASE | re.DOTALL)
        if match:
            node_id = f"meta:{name}"
            _add(nodes, node_id, "html-metadata", path="index.html", mutable=True,
                 operations=["replace_text"], span=[match.start(), match.end()])
            edges.add(("file:index.html", node_id, "contains"))
    local_refs: set[str] = set()
    external_refs: set[str] = set()
    for _, target in parser.references:
        if target.startswith(("#", "mailto:", "tel:", "data:")):
            continue
        if target.startswith(("https://", "http://")):
            external_refs.add(target)
            continue
        clean = target.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if clean and (repo / clean).is_file():
            local_refs.add(clean)
    for path in sorted(local_refs):
        node_id = f"file:{path}"
        if node_id not in nodes:
            _add(nodes, node_id, "asset", path=path, mutable=True,
                 operations=["replace_text"] if (repo / path).suffix in {".svg", ".css", ".js"} else [])
        edges.add(("file:index.html", node_id, "references"))
    for target in sorted(external_refs):
        if target == config["paper_url"]:
            node_id = "external:paper"
        else:
            node_id = "external:" + hashlib.sha256(target.encode()).hexdigest()[:10]
        _add(nodes, node_id, "external-source", url=target)
        edges.add(("file:index.html", node_id, "links-to"))
    _add(nodes, "external:repository-metadata", "external-owned", url=config.get("repo_url"),
         mutable=False, operations=["manual-admin-edit"])
    _add(nodes, "external:paper-backlink", "external-owned", url=config["paper_url"],
         mutable=False, operations=["author-edit"], state="unverified")
    if "file:README.md" in nodes:
        edges.add(("external:repository-metadata", "file:README.md", "describes"))
        if config["site_url"] in (repo / "README.md").read_text(encoding="utf-8"):
            edges.add(("file:README.md", "file:index.html", "links-to"))
    if "file:robots.txt" in nodes and "file:sitemap.xml" in nodes:
        edges.add(("file:robots.txt", "file:sitemap.xml", "declares"))
    if "file:sitemap.xml" in nodes and "file:index.html" in nodes:
        edges.add(("file:sitemap.xml", "file:index.html", "lists"))
    _add(nodes, "outcome:site-discovery", "unobserved-outcome")
    for dependency in ("file:index.html", "file:robots.txt", "file:sitemap.xml",
                       "file:README.md", "external:repository-metadata",
                       "external:paper-backlink"):
        if dependency in nodes:
            edges.add(("outcome:site-discovery", dependency, "depends-on"))
    for name in config["platforms"]:
        index = f"outcome:{name}:retrieval"
        answer = f"outcome:{name}:answer"
        _add(nodes, index, "observed-outcome", platform=name)
        _add(nodes, answer, "observed-outcome", platform=name)
        edges.add((index, "outcome:site-discovery", "depends-on"))
        edges.add((answer, index, "depends-on"))
        if "external:paper" in nodes:
            edges.add((index, "external:paper", "may-retrieve"))
    return {"nodes": list(nodes.values()), "edges": [
        {"from": a, "to": b, "kind": k} for a, b, k in sorted(edges)],
        "site_url": config["site_url"], "paper_url": config["paper_url"]}


def readiness(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    def content(name: str) -> str:
        path = repo / name
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    home, readme, robots, sitemap = (content(name) for name in
                                     ("index.html", "README.md", "robots.txt", "sitemap.xml"))
    checks = {
        "homepage_html": bool(home and "<html" in home.lower()),
        "title": bool(re.search(r"<title>[^<]{15,}</title>", home, re.I)),
        "description": bool(re.search(r'<meta\s+name=["\']description["\']', home, re.I)),
        "canonical": config["site_url"] in home and "canonical" in home,
        "schema": "application/ld+json" in home and config["paper_url"] in home,
        "robots_allows": "Allow: /" in robots and "Disallow: /" not in robots,
        "sitemap": config["site_url"] in sitemap,
        "topic_summary": "co-evolution" in home.lower() and "meta-agent" in home.lower(),
        "source_links": config["paper_url"] in home and home.count("https://arxiv.org/abs/") >= 3,
        "repository_backlink": config["site_url"] in readme and "co-evolution" in readme.lower(),
    }
    return {"score": sum(checks.values()) * 10, "max_score": 100,
            "checks": checks, "kind": "local-readiness-proxy",
            "warning": "This score does not measure indexing, retrieval, mentions, or citations."}


def _safe_path(repo: Path, relative: str) -> Path:
    path = (repo / relative).resolve()
    if not path.is_relative_to(repo.resolve()) or not path.is_file():
        raise ValueError(f"path must be an existing file inside repo: {relative}")
    return path


def apply_operations(repo: Path, config: dict[str, Any], operations: list[dict[str, Any]],
                     *, write: bool = False) -> dict[str, Any]:
    """Apply graph-addressed edits in memory; write only after every operation validates."""
    graph = build_graph(repo, config)
    allowed = {node["id"]: node for node in graph["nodes"] if node["mutable"]}
    changed: dict[str, str] = {}
    originals: dict[str, str] = {}
    for step in operations:
        op, node_id = step.get("op"), step.get("node")
        node = allowed.get(node_id)
        if node is None or op not in node["operations"]:
            raise ValueError(f"unsupported operation {op!r} on graph node {node_id!r}")
        relative = node["path"]
        path = _safe_path(repo, relative)
        old = changed.get(relative, path.read_text(encoding="utf-8"))
        originals.setdefault(relative, old)
        if op == "replace_text":
            before, after = step.get("before"), step.get("after")
            if not before or not isinstance(after, str) or old.count(before) != 1:
                raise ValueError("replace_text requires one exact before match and an after string")
            new = old.replace(before, after, 1)
        else:
            if relative != "index.html":
                raise ValueError("section operations require index.html")
            parser = SectionParser(old)
            parser.feed(old)
            section_id = node_id.removeprefix("section:")
            if section_id not in parser.sections:
                raise ValueError(f"section disappeared: {section_id}")
            start, end = parser.sections[section_id]
            if op == "edit":
                html = step.get("html", "")
                if not re.search(rf'<section\b[^>]*\bid=["\']{re.escape(section_id)}["\']', html):
                    raise ValueError("edited section must retain its id")
                new = old[:start] + html + old[end:]
            elif op == "add_after":
                html = step.get("html", "")
                match = re.search(r'<section\b[^>]*\bid=["\']([^"\']+)["\']', html)
                if not match or match.group(1) in parser.sections:
                    raise ValueError("new section needs a unique id")
                new = old[:end] + "\n" + html + old[end:]
            elif op == "move_after":
                target = step.get("after_node", "").removeprefix("section:")
                if target not in parser.sections or target == section_id:
                    raise ValueError("move_after needs a different existing section")
                target_end = parser.sections[target][1]
                block = old[start:end]
                without = old[:start] + old[end:]
                if target_end > start:
                    target_end -= end - start
                new = without[:target_end] + "\n" + block + without[target_end:]
            elif op == "remove":
                new = old[:start] + old[end:]
            else:
                raise ValueError(f"unknown operation: {op}")
        changed[relative] = new
    diffs = {name: "".join(difflib.unified_diff(originals[name].splitlines(True),
                                                  changed[name].splitlines(True),
                                                  fromfile=f"a/{name}", tofile=f"b/{name}"))
             for name in changed}
    if write:
        for name, value in changed.items():
            _safe_path(repo, name).write_text(value, encoding="utf-8")
    return {"applied": write, "files": sorted(changed), "diffs": diffs}


def _binary_metric(value: str, field: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    if field.endswith("_rank"):
        rank = int(value)
        if rank < 0:
            raise ValueError("rank must be nonnegative")
        return float(rank > 0)
    if value not in {"0", "1"}:
        raise ValueError(f"{field} must be 0, 1, or blank")
    return float(value)


def load_observations(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"phase", "provider", "query", "project_rank", "paper_rank",
                "project_cited", "answer_accurate"}
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"observation CSV missing {sorted(required - set(rows[0]))}")
    for row in rows:
        if row["phase"] not in {"before", "after"}:
            raise ValueError("phase must be before or after")
        for field in METRIC_WEIGHTS:
            value = row.get(field, row.get("eau_mentioned", "") if field == "target_mentioned" else "")
            _binary_metric(value or "", field)
    return rows


def compare_platforms(config: dict[str, Any], rows: list[dict[str, str]],
                      candidate: str | None = None) -> dict[str, Any]:
    """Pair like-for-like query/metric cells and expose missing global weight.

    A positive outcome is certified only when its worst-case unknown cells remain
    positive and no measured platform exceeds the permitted regression.
    """
    platforms = config["platforms"]
    total_platform_weight = sum(float(v) for v in platforms.values())
    metrics = config.get("metric_weights", METRIC_WEIGHTS)
    if abs(sum(float(v) for v in metrics.values()) - 1.0) > 1e-8:
        raise ValueError("metric_weights must sum to 1")
    queries = config.get("queries", [])
    query_names = [item["text"] if isinstance(item, dict) else item for item in queries]
    if not query_names:
        query_names = sorted({row["query"] for row in rows})
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["provider"] not in platforms or row["query"] not in query_names:
            continue
        row_candidate = row.get("candidate_id", "") or "baseline"
        if candidate and row["phase"] == "after" and row_candidate != candidate:
            continue
        for field in metrics:
            raw = row.get(field, row.get("eau_mentioned", "") if field == "target_mentioned" else "")
            value = _binary_metric(raw or "", field)
            if value is not None:
                grouped[(row["provider"], row["query"], row["phase"], field)].append(value)
    platform_results: dict[str, Any] = {}
    observed_delta = 0.0
    covered_weight = 0.0
    regressions = []
    for platform, raw_weight in platforms.items():
        platform_weight = float(raw_weight) / total_platform_weight
        cells = []
        platform_delta = 0.0
        platform_coverage = 0.0
        for query in query_names:
            for field, metric_weight in metrics.items():
                before = grouped.get((platform, query, "before", field), [])
                after = grouped.get((platform, query, "after", field), [])
                if not before or not after:
                    continue
                delta = sum(after) / len(after) - sum(before) / len(before)
                cell_weight = float(metric_weight) / len(query_names)
                platform_delta += cell_weight * delta
                platform_coverage += cell_weight
                cells.append({"query": query, "metric": field, "before_n": len(before),
                              "after_n": len(after), "delta": round(delta, 6)})
        observed_delta += platform_weight * platform_delta
        covered_weight += platform_weight * platform_coverage
        if cells and platform_delta < -float(config.get("max_platform_regression", 0.05)):
            regressions.append(platform)
        platform_results[platform] = {"delta_known_cells": round(platform_delta, 6),
                                      "coverage": round(platform_coverage, 6), "cells": cells}
    unknown = 1.0 - covered_weight
    bounds = [observed_delta - unknown, observed_delta + unknown]
    minimum = float(config.get("min_comparison_coverage", 0.8))
    certified = covered_weight >= minimum and bounds[0] > 0 and not regressions
    return {"platforms": platform_results, "observed_weight": round(covered_weight, 6),
            "weighted_delta_known_cells": round(observed_delta, 6),
            "global_delta_bounds": [round(x, 6) for x in bounds],
            "regressions": regressions,
            "verdict": "keep" if certified else "insufficient_evidence_or_regression",
            "warning": "Unknown observations are bounded, never imputed as zero; local readiness is excluded."}


def prioritize(graph: dict[str, Any], config: dict[str, Any],
               observations: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
    """Order certified global gains first, then structural hypotheses.

    A measured platform regression sends an intervention below unmeasured ideas.
    Unknown platform effects never become positive evidence.
    """
    parents: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        parents[edge["to"]].add(edge["from"])
    result = []
    for item in config.get("interventions", []):
        reached = set()
        frontier = list(item["nodes"])
        while frontier:
            node = frontier.pop()
            for parent in parents[node]:
                if parent not in reached:
                    reached.add(parent)
                    frontier.append(parent)
        outcomes = [node for node in reached if node.startswith("outcome:")]
        cost = max(float(item.get("cost", 1)), 0.1)
        gap = bool(item.get("current_gap", True))
        score = round((len(outcomes) + 1) * int(gap) / cost, 3)
        evidence = (compare_platforms(config, observations, item.get("candidate_id"))
                    if observations is not None and item.get("candidate_id") else None)
        state = ("certified_gain" if evidence and evidence["verdict"] == "keep"
                 else "observed_regression" if evidence and evidence["regressions"]
                 else "hypothesis_only")
        result.append({"id": item["id"], "nodes": item["nodes"],
                       "reachable_outcomes": sorted(outcomes), "structural_priority": score,
                       "current_gap": gap, "owner": item.get("owner", "repo"),
                       "status": state, "global_evaluation": evidence})
    rank = {"certified_gain": 0, "hypothesis_only": 1, "observed_regression": 2}
    return sorted(result, key=lambda entry: (rank[entry["status"]],
                                            -entry["structural_priority"], entry["id"]))
