"""The eval matrix: one row per knowledge-map keyword, one column per signal.

Columns:
  site     the keyword is stated in visible text (homepage for hop 0, any page otherwise)
  schema   the keyword appears in JSON-LD structured data
  llms     the keyword appears in llms.txt
  llm      a model reading only the site answers that keyword's questions correctly
  search   searching the keyword's queries surfaces the entity (recorded probes)

A cell is a value in [0, 1], or None when that signal was not measured for the
row (no question for it, LLM test skipped, no probe recorded). Row weights come
from the hop: the core counts most.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .kmap import KnowledgeMap, Node, contains_any
from .llm import LLMResult
from .site import Site

COLUMNS = ["site", "snippet", "schema", "llms", "llm", "search"]
# Columns that can be computed from a local build, and their weights. `snippet`
# (metric v2) is the keyword appearing where a search result would show it.
OFFLINE_COLUMNS = {"site": 0.5, "schema": 0.3, "llms": 0.2}
OFFLINE_COLUMNS_V2 = {"site": 0.3, "snippet": 0.25, "schema": 0.25, "llms": 0.2}


@dataclass
class Row:
    node: str
    hop: int
    kind: str
    keyword: str
    weight: float
    cells: dict[str, float | None]
    queries: list[str] = field(default_factory=list)


@dataclass
class Matrix:
    rows: list[Row]

    def column_score(self, column: str, hop: int | None = None) -> float | None:
        """Weighted mean of the measured cells in a column (0-1), or None if none measured."""
        cells = [
            (row.weight, row.cells[column])
            for row in self.rows
            if row.cells.get(column) is not None and (hop is None or row.hop == hop)
        ]
        if not cells:
            return None
        return sum(weight * value for weight, value in cells) / sum(weight for weight, _ in cells)

    def offline_score(self) -> float:
        """0-100 score over the locally computable columns."""
        weights = OFFLINE_COLUMNS_V2 if self.column_score("snippet") is not None else OFFLINE_COLUMNS
        parts = [(weight, self.column_score(column)) for column, weight in weights.items()]
        measured = [(weight, value) for weight, value in parts if value is not None]
        if not measured:
            return 0.0
        return round(100 * sum(w * v for w, v in measured) / sum(w for w, _ in measured), 2)

    def summary(self) -> dict[str, Any]:
        return {
            column: {
                "all": _round(self.column_score(column)),
                **{f"hop{hop}": _round(self.column_score(column, hop)) for hop in (0, 1, 2)},
            }
            for column in COLUMNS
        }

    def to_dict(self) -> dict[str, Any]:
        return {"columns": COLUMNS, "summary": self.summary(), "rows": [row.__dict__ for row in self.rows]}

    def to_markdown(self) -> str:
        lines = [
            "| keyword | hop | " + " | ".join(COLUMNS) + " |",
            "| --- | --- | " + " | ".join("---" for _ in COLUMNS) + " |",
        ]
        for row in sorted(self.rows, key=lambda r: (r.hop, r.node)):
            lines.append(
                f"| {row.keyword} | {row.hop} | " + " | ".join(_cell(row.cells.get(c)) for c in COLUMNS) + " |"
            )
        summary = self.summary()
        lines.append("| **column score** | | " + " | ".join(_cell(summary[c]["all"]) for c in COLUMNS) + " |")
        return "\n".join(lines)

    def to_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["node", "keyword", "hop", "kind", *COLUMNS, "queries"])
        for row in self.rows:
            writer.writerow(
                [row.node, row.keyword, row.hop, row.kind, *("" if row.cells.get(c) is None else row.cells[c] for c in COLUMNS), " | ".join(row.queries)]
            )
        return buffer.getvalue()


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def _cell(value: float | None) -> str:
    if value is None:
        return "-"
    if value in (0, 1):
        return "✓" if value == 1 else "✗"
    return f"{value:.2f}"


def build_matrix(
    site: Site,
    kmap: KnowledgeMap,
    llm: LLMResult | None = None,
    probes: list[dict[str, Any]] | None = None,
    snippet_chars: int | None = None,
) -> Matrix:
    home_text = site.home.visible_text if site.home else ""
    home_snippet = site.home.snippet(snippet_chars) if site.home and snippet_chars else ""
    site_snippets = " ".join(page.snippet(snippet_chars) for page in site.pages.values()) if snippet_chars else ""
    site_text = site.all_visible_text()
    schema_text = json.dumps(site.all_json_ld(), ensure_ascii=False)
    llms_text = site.llms_txt or ""
    probe_index = _index_probes(probes or [])

    rows = []
    for node in kmap.nodes:
        rows.append(
            Row(
                node=node.id,
                hop=node.hop,
                kind=node.kind,
                keyword=node.terms[0],
                weight=node.weight,
                queries=kmap.queries_for(node),
                cells={
                    "site": float(contains_any(home_text if node.hop == 0 else site_text, node.terms)),
                    "snippet": (
                        float(contains_any(home_snippet if node.hop == 0 else site_snippets, node.terms))
                        if snippet_chars
                        else None
                    ),
                    "schema": float(contains_any(schema_text, node.terms)),
                    "llms": float(contains_any(llms_text, node.terms)) if site.llms_txt is not None else 0.0,
                    "llm": _llm_cell(node, llm),
                    "search": _search_cell(kmap.queries_for(node), probe_index),
                },
            )
        )
    return Matrix(rows)


def _llm_cell(node: Node, llm: LLMResult | None) -> float | None:
    if llm is None:
        return None
    answers = [answer for answer in llm.answers if answer.get("node") == node.id]
    if not answers:
        return None
    return sum(1.0 for answer in answers if answer["correct"]) / len(answers)


def _index_probes(probes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Latest result per (query, engine)."""
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for record in sorted(probes, key=lambda r: r.get("recorded_at", "")):
        latest[(record["query"].strip().lower(), record.get("engine", ""))] = record
    index: dict[str, list[dict[str, Any]]] = {}
    for (query, _engine), record in latest.items():
        index.setdefault(query, []).append(record)
    return index


def _search_cell(queries: list[str], index: dict[str, list[dict[str, Any]]]) -> float | None:
    records = [record for query in queries for record in index.get(query.strip().lower(), [])]
    if not records:
        return None
    return sum(1.0 for record in records if record.get("found")) / len(records)


def load_probes(path: str | Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
