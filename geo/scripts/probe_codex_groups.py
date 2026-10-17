#!/usr/bin/env python3
"""Run Codex web probes in bounded groups without overloading Codex startup."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--groups", type=int, default=5)
    parser.add_argument("--parallelism", type=int, default=2, choices=(1, 2))
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    queries = [q for q in Path(args.queries).read_text().splitlines() if q.strip()]
    group_count = max(1, min(args.groups, len(queries)))
    groups = [queries[i::group_count] for i in range(group_count)]
    script = Path(__file__).with_name("probe_codex.sh")
    output = Path(args.answers).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="codex-probe-groups-") as temp:
        root = Path(temp)

        def run_group(item: tuple[int, list[str]]) -> tuple[int, int, Path]:
            index, values = item
            query_file = root / f"queries-{index:02d}.txt"
            answer_file = root / f"answers-{index:02d}.jsonl"
            query_file.write_text("\n".join(values) + "\n")
            env = os.environ.copy()
            env["CODEX_SEARCH_TIMEOUT"] = str(args.timeout)
            result = subprocess.run(["bash", str(script), str(query_file), str(answer_file)], env=env)
            return index, result.returncode, answer_file

        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            results = list(pool.map(run_group, enumerate(groups)))

        answers: dict[str, dict] = {}
        final_logs = Path(str(output) + ".logs")
        final_logs.mkdir(parents=True, exist_ok=True)
        failed = False
        for index, code, path in sorted(results):
            failed |= code != 0
            group_logs = path.with_suffix("").with_suffix(".logs")
            if group_logs.is_dir():
                for log in sorted(group_logs.glob("*.log")):
                    shutil.copy2(log, final_logs / f"group-{index:02d}-{log.name}")
            for line in path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    answers[row["query"]] = row
        with output.open("w") as handle:
            for query in queries:
                row = answers.get(query, {"query": query, "text": "", "status": "missing", "exit_code": -1, "elapsed_seconds": 0})
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
