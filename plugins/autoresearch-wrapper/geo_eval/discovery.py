"""The discovery matrix: does each engine surface the entity for each keyword's query?

Rows are knowledge-map queries; columns are search engines and search-enabled
answer engines. Every answer is judged by the same rule, so the columns are
comparable:

  found      the answer cites the entity's own site, or names the entity (name or
             alias) together with an attribution term (e.g. its affiliation) in
             the same line or sentence
  rank       position of the entity's site among the distinct URLs the answer
             cites, when it is cited at all

Answers come in as text, collected by any means (a search tool, a CLI agent, or a
human pasting results), and are judged here.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from .kmap import HOP_WEIGHTS, KnowledgeMap, contains_any

URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")


@dataclass
class Judgement:
    found: bool
    site_cited: bool
    attributed: bool
    rank: int | None
    url: str | None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def attribution_terms(kmap: KnowledgeMap) -> list[str]:
    """Terms that tie the name to the right person (default: the affiliation node)."""
    configured = kmap.limits.get("attribution_terms") or []
    if configured:
        return list(configured)
    node = kmap.node("affiliation")
    if node:
        return node.terms
    return [term for node in kmap.by_hop(0) for term in node.terms]


def corroborating_terms(kmap: KnowledgeMap, query: str | None) -> list[str]:
    """True facts from the map that the query did not already contain.

    Without this, an engine that echoes the query ("Min Cai, University of Alberta")
    and invents the rest counts as having found the entity. Models answering from
    memory do exactly that.
    """
    attribution = {term.lower() for term in attribution_terms(kmap)}
    # Only hop >= 1 facts (papers, collaborators, education, topics) corroborate. Core
    # facts are guessable from the query: a model that hears "University of Alberta"
    # will add "Edmonton" while inventing everything else.
    terms = [
        term
        for node in kmap.nodes
        if node.hop >= 1
        for term in node.terms
        if term.lower() not in attribution and len(term) >= 3
    ]
    if query:
        terms = [term for term in terms if not contains_any(query, [term])]
    return terms


def judge_answer(text: str, kmap: KnowledgeMap, query: str | None = None) -> Judgement:
    site_host = _host(kmap.url) if kmap.url else ""
    urls: list[str] = []
    for match in URL_RE.findall(text):
        url = match.rstrip(".,;:!?*_")
        if url not in urls:
            urls.append(url)
    rank = next((index + 1 for index, url in enumerate(urls) if site_host and _host(url) == site_host), None)
    site_cited = rank is not None or (bool(site_host) and site_host in text.lower())

    terms = attribution_terms(kmap)
    chunks = re.split(r"\n+|(?<=[.!?])\s+", text)
    named_with_affiliation = any(
        contains_any(chunk, kmap.identity_terms) and contains_any(chunk, terms) for chunk in chunks
    )
    attributed = named_with_affiliation and contains_any(text, corroborating_terms(kmap, query))
    return Judgement(
        found=site_cited or attributed,
        site_cited=site_cited,
        attributed=attributed,
        rank=rank,
        url=urls[rank - 1] if rank else None,
    )


def probe_record(query: str, engine: str, judgement: Judgement, note: str = "", excerpt: str = "") -> dict[str, Any]:
    return {
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "query": query,
        "engine": engine,
        **judgement.to_dict(),
        "judged_by": "geo_eval",
        "note": note,
        "excerpt": excerpt[:400],
    }


def all_queries(kmap: KnowledgeMap, max_hop: int | None = None) -> list[dict[str, Any]]:
    candidates = [
        {"node": node.id, "hop": node.hop, "keyword": node.terms[0], "query": query}
        for node in sorted(kmap.nodes, key=lambda n: (n.hop, n.id))
        if max_hop is None or node.hop <= max_hop
        for query in kmap.queries_for(node)
    ]
    candidates += [
        {"node": None, "hop": probe.get("hop", 1), "keyword": probe["query"], "query": probe["query"]}
        for probe in kmap.probes
        if max_hop is None or probe.get("hop", 1) <= max_hop
    ]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in candidates:
        key = row["query"].strip().lower()
        if key not in seen:
            rows.append(row)
            seen.add(key)
    return rows


def is_search_engine(engine: str | None) -> bool:
    """Memory-only model answers are not search-engine observations."""
    return not (engine or "").startswith("memory:")


@dataclass
class DiscoveryMatrix:
    rows: list[dict[str, Any]]
    engines: list[str]
    cells: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def column_score(self, engine: str, hop: int | None = None) -> float | None:
        measured = [
            (HOP_WEIGHTS.get(row["hop"], 1.0), 1.0 if self.cells[(row["query"], engine)]["found"] else 0.0)
            for row in self.rows
            if (row["query"], engine) in self.cells and (hop is None or row["hop"] == hop)
        ]
        if not measured:
            return None
        return sum(w * v for w, v in measured) / sum(w for w, _ in measured)

    def summary(self) -> dict[str, Any]:
        return {
            engine: {
                "all": _r(self.column_score(engine)),
                **{f"hop{h}": _r(self.column_score(engine, h)) for h in (0, 1, 2)},
                "found": sum(1 for row in self.rows if self.cells.get((row["query"], engine), {}).get("found")),
                "probed": sum(1 for row in self.rows if (row["query"], engine) in self.cells),
            }
            for engine in self.engines
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "engines": self.engines,
            "summary": self.summary(),
            "rows": [
                {**row, "cells": {engine: self.cells.get((row["query"], engine)) for engine in self.engines}}
                for row in self.rows
            ],
        }

    def to_markdown(self) -> str:
        header = "| query | hop | " + " | ".join(self.engines) + " |"
        lines = [header, "| --- | --- | " + " | ".join("---" for _ in self.engines) + " |"]
        for row in self.rows:
            cells = []
            for engine in self.engines:
                cell = self.cells.get((row["query"], engine))
                if cell is None:
                    cells.append("-")
                elif cell["found"]:
                    cells.append(f"✓{cell['rank']}" if cell.get("rank") else "✓")
                else:
                    cells.append("✗")
            lines.append(f"| {row['query']} | {row['hop']} | " + " | ".join(cells) + " |")
        summary = self.summary()
        lines.append(
            "| **found** | | "
            + " | ".join(f"{summary[e]['found']}/{summary[e]['probed']}" for e in self.engines)
            + " |"
        )
        return "\n".join(lines)


def _r(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def build_discovery(kmap: KnowledgeMap, probes: list[dict[str, Any]]) -> DiscoveryMatrix:
    """Latest record per (query, engine); rows follow the map's queries, then any extra probed queries."""
    rows = all_queries(kmap)
    known = {row["query"].strip().lower() for row in rows}
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for record in sorted(probes, key=lambda r: r.get("recorded_at", "")):
        engine = record.get("engine") or "unspecified"
        if is_search_engine(engine):
            latest[(record["query"].strip().lower(), engine)] = record
    for (query, _engine), record in latest.items():
        if query not in known:
            rows.append({"node": None, "hop": 1, "keyword": record["query"], "query": record["query"]})
            known.add(query)
    engines = sorted({engine for _query, engine in latest})
    cells = {}
    for row in rows:
        for engine in engines:
            record = latest.get((row["query"].strip().lower(), engine))
            if record is not None:
                cells[(row["query"], engine)] = {"found": bool(record.get("found")), "rank": record.get("rank"), "url": record.get("url")}
    return DiscoveryMatrix(rows=rows, engines=engines, cells=cells)


def judge_answers_file(kmap: KnowledgeMap, lines: list[str], engine: str, note: str = "") -> list[dict[str, Any]]:
    """Judge a JSONL of {"query", "text"} answers collected from any engine."""
    records = []
    for line in lines:
        if not line.strip():
            continue
        item = json.loads(line)
        text = str(item.get("text", ""))
        records.append(probe_record(item["query"], engine, judge_answer(text, kmap, item["query"]), item.get("note", note), text))
    return records
