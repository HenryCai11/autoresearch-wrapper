#!/usr/bin/env python3
"""Build plotting-ready inner/outer GEO metrics for one deployed EAU run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from geo_eval.kmap import contains_any, load_map


ENGINES = {
    "gpt-web": "gpt-web-answers.jsonl",
    "codex-search": "codex-answers-complete.jsonl",
    "tavily-search": "tavily-answers.jsonl",
    "exa-search": "exa-answers.jsonl",
}
OUTER_WEIGHTS = {"citation_rate": 0.45, "attribution_rate": 0.25, "mrr": 0.20, "mention_rate": 0.10}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--map", required=True)
    args = parser.parse_args()
    root = Path(args.run_dir)
    kmap = load_map(args.map)
    queries = root.joinpath("queries.txt").read_text().splitlines()
    tiers = {q: ("exact" if i < 5 else "fuzzy" if i < 10 else "broad") for i, q in enumerate(queries)}

    probes = {(row["query"], row["engine"]): row for row in read_jsonl(root / "search-probes.jsonl")}
    answers: dict[tuple[str, str], str] = {}
    for engine, filename in ENGINES.items():
        for row in read_jsonl(root / filename):
            answers[(row["query"], engine)] = str(row.get("text", ""))

    rows = []
    for query in queries:
        for engine in ENGINES:
            probe = probes.get((query, engine), {})
            text = answers.get((query, engine), "")
            rows.append({
                "query": query,
                "tier": tiers[query],
                "engine": engine,
                "mention": contains_any(text, kmap.identity_terms),
                "found": bool(probe.get("found")),
                "site_cited": bool(probe.get("site_cited")),
                "attributed": bool(probe.get("attributed")),
                "rank": probe.get("rank"),
                "reciprocal_rank": 1.0 / probe["rank"] if probe.get("rank") else 0.0,
                "url": probe.get("url"),
                "answer_empty": not bool(text.strip()),
            })

    with (root / "search-matrix.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)

    def stats(items: list[dict]) -> dict:
        n = len(items)
        return {
            "probed": n,
            "answer_success_rate": round(mean([not r["answer_empty"] for r in items]), 4),
            "mention_rate": round(mean([r["mention"] for r in items]), 4),
            "found_rate": round(mean([r["found"] for r in items]), 4),
            "citation_rate": round(mean([r["site_cited"] for r in items]), 4),
            "attribution_rate": round(mean([r["attributed"] for r in items]), 4),
            "mrr": round(mean([r["reciprocal_rank"] for r in items]), 4),
        }

    overall = stats(rows)
    outer_score = 100 * sum(OUTER_WEIGHTS[key] * overall[key] for key in OUTER_WEIGHTS)
    outer = {
        "definition": "macro average over 15 fixed queries × 4 engines",
        "weights": OUTER_WEIGHTS,
        "score": round(outer_score, 2),
        "overall": overall,
        "by_engine": {engine: stats([r for r in rows if r["engine"] == engine]) for engine in ENGINES},
        "by_tier": {tier: stats([r for r in rows if r["tier"] == tier]) for tier in ("exact", "fuzzy", "broad")},
    }
    (root / "outer-summary.json").write_text(json.dumps(outer, ensure_ascii=False, indent=2) + "\n")

    offline = json.loads((root / "offline-report.json").read_text())
    run = json.loads((root / "run.json").read_text())
    summary = {
        "experiment_id": run["experiment_id"], "round": run["round"], "label": run["label"],
        "change_id": run["change_id"], "production_merge_commit": run["production_merge_commit"],
        "inner_loop": {"score": offline["metric"], "matrix_offline": offline["matrix_offline"], "technical": offline["technical"]["score"]},
        "outer_loop": outer,
    }
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
