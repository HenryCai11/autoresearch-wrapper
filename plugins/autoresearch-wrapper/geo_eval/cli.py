"""geo-eval command line.

  geo_eval validate --map map.json
  geo_eval matrix   --map map.json --site _site/ [--no-llm] [--probes probes.jsonl] [--report out.json]
  geo_eval queries  --map map.json
  geo_eval probe-record --probes probes.jsonl --query "..." --found|--not-found [--rank N] [--engine NAME]
  geo_eval ood      --goatcounter CODE --token-file FILE [--days 7] [--log ood.jsonl]

`matrix` prints the eval matrix and ends with METRIC=<0-100>, the line
autoresearch-wrapper reads. A guardrail violation prints GUARDRAIL lines and
exits 3 without a METRIC, so the candidate is recorded as a crash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from .discovery import all_queries, build_discovery, judge_answers_file, probe_llm_memory
from .kmap import MapError, load_map
from .llm import DEFAULT_BASE_URL, LLMError, chat, load_api_key, score_llm
from .matrix import build_matrix, load_probes
from .offline import score_technical
from .ood import OODError, goatcounter_snapshot, snapshot_from_dir
from .site import load_site

DEFAULT_SCORING = {"offline": 0.5, "llm": 0.5, "matrix_share_of_offline": 0.6}
EXIT_GUARDRAIL = 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geo_eval", description="Generative engine optimization eval toolkit.")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Check a knowledge map.")
    validate.add_argument("--map", required=True)
    validate.set_defaults(func=cmd_validate)

    matrix = sub.add_parser("matrix", help="Score a site: eval matrix + METRIC line.")
    matrix.add_argument("--map", required=True)
    matrix.add_argument("--site", required=True, help="Built site directory or live base URL.")
    matrix.add_argument("--no-llm", action="store_true", help="Skip the LLM comprehension test.")
    matrix.add_argument("--samples", type=int, default=1, help="LLM replies to average (damps noise).")
    matrix.add_argument("--model", help="LLM model id (default: GEO_LLM_MODEL or gpt-oss-120b).")
    matrix.add_argument("--probes", help="JSONL of recorded search probes (fills the search column).")
    matrix.add_argument("--report", help="Write the full JSON report here.")
    matrix.add_argument("--format", choices=("markdown", "csv", "json"), default="markdown")
    matrix.set_defaults(func=cmd_matrix)

    queries = sub.add_parser("queries", help="List the search queries for each keyword.")
    queries.add_argument("--map", required=True)
    queries.add_argument("--json", action="store_true")
    queries.set_defaults(func=cmd_queries)

    record = sub.add_parser("probe-record", help="Record one search probe result.")
    record.add_argument("--probes", required=True)
    record.add_argument("--query", required=True)
    found = record.add_mutually_exclusive_group(required=True)
    found.add_argument("--found", dest="found", action="store_true", help="The entity or its site surfaced.")
    found.add_argument("--not-found", dest="found", action="store_false")
    record.add_argument("--rank", type=int, help="Position of the entity's site among results, if listed.")
    record.add_argument("--engine", default="unspecified", help="Search or answer engine used.")
    record.add_argument("--url", help="The result URL that surfaced, if any.")
    record.add_argument("--note", default="")
    record.set_defaults(func=cmd_probe_record)

    judge = sub.add_parser("probe-judge", help="Judge collected answers ({query, text} JSONL) from any engine.")
    judge.add_argument("--map", required=True)
    judge.add_argument("--probes", required=True, help="Probe log to append judged records to.")
    judge.add_argument("--answers", required=True, help="JSONL with one {\"query\", \"text\"} object per line.")
    judge.add_argument("--engine", required=True, help="Engine name for the column, e.g. codex-search.")
    judge.add_argument("--note", default="")
    judge.set_defaults(func=cmd_probe_judge)

    memory = sub.add_parser("probe-memory", help="Ask LLMs with no web access, from memory, for every map query.")
    memory.add_argument("--map", required=True)
    memory.add_argument("--probes", required=True)
    memory.add_argument("--model", action="append", required=True, help="Model id; repeat for several.")
    memory.add_argument("--answers-dir", help="Save each model's full answers here as <engine>.jsonl, for re-judging.")
    memory.set_defaults(func=cmd_probe_memory)

    discovery = sub.add_parser("discovery", help="Discovery matrix: query × engine.")
    discovery.add_argument("--map", required=True)
    discovery.add_argument("--probes", required=True)
    discovery.add_argument("--since", help="Only use probes recorded at or after this ISO time.")
    discovery.add_argument("--format", choices=("markdown", "json"), default="markdown")
    discovery.add_argument("--report", help="Write the JSON matrix here.")
    discovery.set_defaults(func=cmd_discovery)

    ood = sub.add_parser("ood", help="Log a real-traffic snapshot (GoatCounter).")
    ood.add_argument("--goatcounter", required=True, help="GoatCounter site code.")
    ood.add_argument("--token-file", default="~/.config/goatcounter/token")
    ood.add_argument("--days", type=int, default=7)
    ood.add_argument("--log", help="Append the snapshot to this JSONL file.")
    ood.add_argument(
        "--input-dir",
        help="Summarise responses saved by geo/scripts/fetch_goatcounter.sh instead of fetching (no internet needed).",
    )
    ood.set_defaults(func=cmd_ood)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (MapError, LLMError, OODError, FileNotFoundError, ConnectionError) as exc:
        print(f"geo_eval: {exc}", file=sys.stderr)
        return 2


def cmd_validate(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    by_hop = {hop: len(kmap.by_hop(hop)) for hop in (0, 1, 2)}
    unasked = [node.id for node in kmap.nodes if not any(q.node == node.id for q in kmap.questions)]
    print(f"entity: {kmap.name} (aliases: {', '.join(kmap.aliases) or 'none'})")
    print(f"nodes: {len(kmap.nodes)} (hop0={by_hop[0]}, hop1={by_hop[1]}, hop2={by_hop[2]}), papers: {len(kmap.papers())}")
    print(f"questions: {len(kmap.questions)}; nodes without a question: {len(unasked)}")
    print(f"forbidden strings: {len(kmap.forbidden)}; limits: {kmap.limits or 'none'}")
    return 0


def cmd_matrix(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    site = load_site(args.site)
    scoring = {**DEFAULT_SCORING, **kmap.scoring}
    version = int(scoring.get("version", 1))
    # Metric v2 reads pages the way search results show them (title, description, opening).
    snippet_chars = int(scoring.get("snippet_chars", 400)) if version >= 2 else None
    context_chars = int(scoring.get("context_chars", 4000 if version >= 2 else 14000))
    technical = score_technical(site, kmap, version=version)
    llm = None if args.no_llm else score_llm(
        site, kmap, model=args.model, samples=args.samples, snippet_chars=snippet_chars, context_chars=context_chars
    )
    matrix = build_matrix(site, kmap, llm=llm, probes=load_probes(args.probes), snippet_chars=snippet_chars)

    share = scoring["matrix_share_of_offline"]
    offline = round(share * matrix.offline_score() + (1 - share) * technical.score, 2)
    if llm is None:
        metric = offline
    else:
        total = scoring["offline"] + scoring["llm"]
        metric = round((scoring["offline"] * offline + scoring["llm"] * llm.score) / total, 2)

    report = {
        "site": site.source,
        "metric_version": version,
        "metric": metric,
        "offline": offline,
        "matrix_offline": matrix.offline_score(),
        "technical": technical.to_dict(),
        "llm": llm.to_dict() if llm else None,
        "matrix": matrix.to_dict(),
        "scoring": scoring,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.format == "csv":
        print(matrix.to_csv(), end="")
    else:
        print(matrix.to_markdown())
        print()
        print("Technical checks lost points on: " + (", ".join(
            f"{c.name} ({c.detail})" for c in technical.checks if c.value < 1
        ) or "nothing"))

    print(f"MATRIX={matrix.offline_score()}")
    print(f"TECHNICAL={technical.score}")
    if llm is not None:
        print(f"LLM={llm.score}")
    if technical.guardrail_violations:
        for violation in technical.guardrail_violations:
            print(f"GUARDRAIL: {violation}")
        return EXIT_GUARDRAIL
    print(f"METRIC={metric}")
    return 0


def cmd_queries(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    rows = [
        {"node": node.id, "hop": node.hop, "query": query}
        for node in sorted(kmap.nodes, key=lambda n: (n.hop, n.id))
        for query in kmap.queries_for(node)
    ]
    rows += [{"node": None, "hop": probe.get("hop"), "query": probe["query"]} for probe in kmap.probes]
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            print(f"{row['hop']}\t{row['node'] or '-'}\t{row['query']}")
    return 0


def cmd_probe_record(args: argparse.Namespace) -> int:
    record = {
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "query": args.query,
        "found": args.found,
        "rank": args.rank,
        "engine": args.engine,
        "url": args.url,
        "note": args.note,
    }
    path = Path(args.probes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0


def _append(path: str, records: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _print_judged(records: list[dict]) -> None:
    for record in records:
        mark = f"found (rank {record['rank']})" if record["found"] and record["rank"] else ("found" if record["found"] else "not found")
        print(f"{record['engine']}\t{mark}\t{record['query']}")


def cmd_probe_judge(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    records = judge_answers_file(kmap, Path(args.answers).read_text().splitlines(), args.engine, args.note)
    _append(args.probes, records)
    _print_judged(records)
    return 0


def cmd_probe_memory(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    queries = [row["query"] for row in all_queries(kmap)]
    key = load_api_key()
    base = os.environ.get("GEO_LLM_BASE_URL", DEFAULT_BASE_URL)
    failures = 0
    for model in args.model:
        try:
            records, answers = probe_llm_memory(
                kmap, queries, model=model,
                ask=lambda prompt, m=model: chat(prompt, model=m, base_url=base, api_key=key, system=None),
            )
        except LLMError as exc:
            print(f"geo_eval: memory:{model}: {exc}", file=sys.stderr)
            failures += 1
            continue
        if args.answers_dir:
            _append(str(Path(args.answers_dir) / f"memory-{model}.jsonl"), answers)
        _append(args.probes, records)
        _print_judged(records)
    return 2 if failures == len(args.model) else 0


def cmd_discovery(args: argparse.Namespace) -> int:
    kmap = load_map(args.map)
    probes = load_probes(args.probes)
    if args.since:
        probes = [p for p in probes if p.get("recorded_at", "") >= args.since]
    matrix = build_discovery(kmap, probes)
    if args.report:
        Path(args.report).write_text(json.dumps(matrix.to_dict(), indent=2, ensure_ascii=False) + "\n")
    if args.format == "json":
        print(json.dumps(matrix.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(matrix.to_markdown())
        for engine, stats in matrix.summary().items():
            print(f"ENGINE {engine}: found {stats['found']}/{stats['probed']}, weighted {stats['all']}")
    return 0


def cmd_ood(args: argparse.Namespace) -> int:
    if args.input_dir:
        snapshot = snapshot_from_dir(args.goatcounter, args.input_dir, args.days)
    else:
        snapshot = goatcounter_snapshot(args.goatcounter, args.token_file, args.days)
    if args.log:
        path = Path(args.log)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return 0
