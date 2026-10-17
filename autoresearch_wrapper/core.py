from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import csv
import datetime as dt
import json
import os
import re
import resource
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath
from string import Template
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX platforms
    fcntl = None

STATE_DIRNAME = ".autoresearch-wrapper"
STATE_FILENAME = "state.json"
STATUS_FILENAME = "STATUS.md"
STATE_LOCK_FILENAME = "state.lock"
STATE_LOCK_TIMEOUT_SECONDS = 300.0
# State critical sections are short (no metric commands run under the lock).
STATE_LOCK_STALE_SECONDS = 600.0
RUNS_DIRNAME = "runs"
DEFAULT_METRIC_REGEX = r"METRIC\s*=\s*(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
WRAP_DEFAULT_ROUNDS = 3
DEFAULT_PARALLELISM = 2
SCHEMA_VERSION = 2

SCHEDULER_COMMANDS = {
    "slurm": ["squeue", "sbatch"],
    "pbs": ["qsub", "qstat"],
}

METRIC_PRESETS = {
    "runtime_seconds": {
        "metric_name": "runtime_seconds",
        "goal": "minimize",
        "description": "Measure wall clock runtime for one script invocation.",
    },
    "latency_ms": {
        "metric_name": "latency_ms",
        "goal": "minimize",
        "description": "Measure end-to-end latency in milliseconds for one script invocation.",
    },
    "throughput": {
        "metric_name": "throughput",
        "goal": "maximize",
        "description": "Measure invocations per second for one script entrypoint.",
    },
    "memory_mb": {
        "metric_name": "memory_mb",
        "goal": "minimize",
        "description": "Measure peak child-process memory usage in megabytes.",
    },
}

CLI_COMMANDS = {
    "wizard",
    "scan",
    "wrap",
    "configure",
    "status",
    "run",
    "allocate",
    "evaluate",
    "record",
    "preset-metric",
    "flow",
    "monitor",
    "create",
    "delete",
    "arm-ready",
    "compare",
    "finalize",
    "geo-graph",
    "geo-score",
    "geo-apply",
    "geo-compare",
    "geo-prioritize",
    "geo-explore",
    "geo-decide",
}

IGNORED_DIRS = {
    ".git",
    STATE_DIRNAME,
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".turbo",
    ".reference-autoresearch",
}

SOURCE_EXTENSIONS = {
    ".html": "html",
    ".css": "css",
    ".svg": "svg",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".m": "objective-c",
    ".mm": "objective-c++",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
}

PATH_HINTS = {
    "latency_ms": ("api", "server", "serve", "rpc", "request", "handler", "infer", "decode"),
    "runtime_seconds": ("train", "search", "solver", "compute", "pipeline", "batch", "etl"),
    "memory_mb": ("cache", "alloc", "memory", "tensor", "image", "dataset"),
    "throughput": ("throughput", "qps", "rps", "stream", "index", "ingest"),
    "accuracy": ("eval", "predict", "classify", "rank", "model"),
    "loss": ("train", "loss", "optimizer", "backprop"),
}

TEXT_HINTS = {
    "latency_ms": ("latency", "p95", "p99", "response time", "slow request"),
    "runtime_seconds": ("runtime", "timeit", "elapsed", "duration", "benchmark"),
    "memory_mb": ("memory", "alloc", "rss", "vram", "oom"),
    "throughput": ("throughput", "qps", "rps", "tokens/s", "req/s"),
    "accuracy": ("accuracy", "f1", "precision", "recall", "auc", "bleu"),
    "loss": ("loss", "val loss", "training loss"),
}

MAXIMIZE_METRICS = {"throughput", "accuracy"}
OPTIMIZATION_KEYWORDS = (
    "optimiz",
    "perf",
    "latency",
    "throughput",
    "benchmark",
    "cache",
    "slow",
    "hot path",
    "vectoriz",
    "parallel",
    "batch",
    "memoiz",
)
STATUS_ORDER = {"surely optimizable": 0, "probably optimizable": 1}
CORE_PATH_HINTS = {
    "src",
    "app",
    "pkg",
    "lib",
    "core",
    "engine",
    "server",
    "service",
    "services",
    "api",
    "model",
    "models",
}
NON_CORE_PATH_HINTS = {
    "test",
    "tests",
    "spec",
    "specs",
    "example",
    "examples",
    "demo",
    "demos",
    "docs",
    "doc",
    "benchmark",
    "benchmarks",
    "bench",
    "fixtures",
    "samples",
    "scripts",
    "tools",
    "migrations",
}
NON_CORE_FILE_HINTS = {
    "__init__.py",
    "conftest.py",
    "setup.py",
    "manage.py",
}
DEFAULT_SCAN_FOCUS_PARTS = 8
DEFAULT_SCAN_FOCUS_SEEDS = 4


# Commands removed in favour of plain instructions in the skills. Without this, an
# unknown first word is treated as a script path for `wrap`.
REMOVED_COMMANDS = {
    "resources": "`resources` was removed: check the machine that runs the metric yourself "
    "(e.g. nproc, nvidia-smi, sinfo) and pass --parallelism to configure.",
    "reference": "`reference` was removed: clone https://github.com/karpathy/autoresearch "
    "yourself if you want the upstream reference.",
}


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] in REMOVED_COMMANDS:
        raise SystemExit(REMOVED_COMMANDS[raw[0]])
    argv = normalize_entry_argv(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dependency-aware autoresearch wrapper helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    wizard = subparsers.add_parser(
        "wizard",
        help="Run the end-to-end interactive workflow: scan, choose a part, configure it, and optionally start a run.",
    )
    add_repo_arg(wizard)
    wizard.add_argument(
        "--full-summary",
        action="store_true",
        help="Print the full language/directory listing and full dependency graph before prompting.",
    )
    add_interactive_arg(wizard)
    wizard.set_defaults(func=command_wizard)

    scan = subparsers.add_parser("scan", help="Analyze the repo and persist part status.")
    add_repo_arg(scan)
    scan.add_argument(
        "--full-summary",
        action="store_true",
        help="Print the full language/directory listing and full dependency graph.",
    )
    add_interactive_arg(scan)
    scan.set_defaults(func=command_scan)

    for name, help_text in (
        ("geo-graph", "Build a site/component/search-outcome dependency graph."),
        ("geo-score", "Measure local GEO readiness, never search exposure."),
        ("geo-apply", "Preview or apply graph-addressed website edits in a worktree."),
        ("geo-compare", "Compare paired platform observations with global regression guards."),
        ("geo-prioritize", "Order next link tests from observed returned source URLs only."),
        ("geo-explore", "Build an evidence-linked GEO experiment tree and HTML explorer."),
        ("geo-decide", "Build a conditional GEO next-action decision tree from real evidence."),
    ):
        geo_parser = subparsers.add_parser(name, help=help_text)
        add_repo_arg(geo_parser)
        geo_parser.add_argument("--config", default="geo/config.json")
        if name == "geo-apply":
            geo_parser.add_argument("--operations", required=True)
            geo_parser.add_argument("--apply", action="store_true")
        if name == "geo-compare":
            geo_parser.add_argument("--observations", default="geo/observations.csv")
            geo_parser.add_argument("--candidate")
        if name in {"geo-prioritize", "geo-explore", "geo-decide"}:
            geo_parser.add_argument("--search-evidence", required=True)
        if name == "geo-explore":
            geo_parser.add_argument("--observations", help="Optional paired before/after CSV.")
            geo_parser.add_argument("--html-out", help="Write an interactive standalone HTML tree.")
        if name == "geo-decide":
            geo_parser.add_argument("--svg-out", help="Write a standalone SVG decision tree.")
        geo_parser.set_defaults(func=command_geo)

    wrap = subparsers.add_parser(
        "wrap",
        help="Wrap a repo-local script path into the dependency-aware autoresearch flow.",
    )
    add_repo_arg(wrap)
    wrap.add_argument("script_path", help="Repo-local script or executable path.")
    wrap.add_argument(
        "--metric-preset",
        choices=sorted(METRIC_PRESETS),
        help="Metric preset to scaffold for this script entrypoint.",
    )
    wrap.add_argument(
        "--metric-command",
        help="Explicit metric command to store immediately.",
    )
    wrap.add_argument(
        "--use-suggested-command",
        action="store_true",
        help="Confirm and store the generated preset metric command.",
    )
    wrap.add_argument(
        "--mode",
        choices=("sequential", "parallel", "wild"),
        default="sequential",
        help="Execution mode for the initial run stub.",
    )
    wrap.add_argument(
        "--rounds",
        type=int,
        default=WRAP_DEFAULT_ROUNDS,
        help="Initial round count for the run stub.",
    )
    wrap.add_argument("--stop-rule", help="Stop rule: " + STOP_RULE_HELP + ".")
    wrap.add_argument("--parallelism", type=int, help="Worker count for parallel mode.")
    wrap.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(wrap)
    wrap.set_defaults(func=command_wrap)

    configure = subparsers.add_parser("configure", help="Persist config for a selected part.")
    add_repo_arg(configure)
    configure.add_argument("--part", help="Part id or relative path.")
    configure.add_argument(
        "--metric-preset",
        choices=sorted(METRIC_PRESETS),
        help="Metric preset helper to apply to this part.",
    )
    configure.add_argument("--metric", help="Metric name.")
    configure.add_argument(
        "--metric-goal",
        choices=("minimize", "maximize"),
        help="How the metric should be optimized.",
    )
    configure.add_argument("--metric-command", help="Shell command that prints the metric.")
    configure.add_argument(
        "--metric-regex",
        default=None,
        help="Regex with a named group 'value' or a first capture group.",
    )
    configure.add_argument(
        "--mode",
        choices=("sequential", "parallel", "wild"),
        help="Execution mode for the optimization loop.",
    )
    configure.add_argument("--rounds", type=int, help="Number of optimization rounds.")
    configure.add_argument("--stop-rule", help="Stop rule: " + STOP_RULE_HELP + ".")
    configure.add_argument(
        "--metric-timeout",
        type=float,
        help="Kill the metric command after this many seconds and record the attempt as a crash.",
    )
    configure.add_argument("--parallelism", type=int, help="Worker count for parallel mode.")
    configure.add_argument(
        "--use-suggested-command",
        action="store_true",
        help="Confirm and store the suggested metric command if one exists.",
    )
    configure.add_argument(
        "--early-exit-patience",
        type=int,
        help="Stop after N rounds without metric improvement.",
    )
    configure.add_argument(
        "--early-exit-threshold",
        type=float,
        help="Minimum improvement to count as progress.",
    )
    configure.add_argument(
        "--wild-max-simultaneous",
        type=int,
        default=None,
        help="Max parameters to change at once in wild mode.",
    )
    add_interactive_arg(configure)
    configure.set_defaults(func=command_configure)

    status = subparsers.add_parser("status", help="Show persisted wrapper status.")
    add_repo_arg(status)
    status.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    status.set_defaults(func=command_status)

    run = subparsers.add_parser("run", help="Initialize or resume an optimization run.")
    add_repo_arg(run)
    run.add_argument("--part", help="Part id to run. Defaults to the selected part.")
    run.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(run)
    run.set_defaults(func=command_run)

    allocate = subparsers.add_parser("allocate", help="Create a candidate worktree.")
    add_repo_arg(allocate)
    allocate.add_argument("--run-id", help="Run id. Defaults to the active run.")
    add_arm_arg(allocate)
    allocate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    allocate.set_defaults(func=command_allocate)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a candidate or seed worktree.")
    add_repo_arg(evaluate)
    evaluate.add_argument("--run-id", help="Run id. Defaults to the active run.")
    evaluate.add_argument("--candidate", required=True, help="Candidate id.")
    add_arm_arg(evaluate)
    add_allow_out_of_scope_arg(evaluate)
    evaluate.add_argument(
        "--timeout",
        type=float,
        help="Override the configured metric timeout (seconds) for this evaluation.",
    )
    evaluate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    evaluate.set_defaults(func=command_evaluate)

    record = subparsers.add_parser("record", help="Persist the result of a candidate evaluation.")
    add_repo_arg(record)
    record.add_argument("--run-id", help="Run id. Defaults to the active run.")
    record.add_argument("--candidate", required=True, help="Candidate id.")
    add_arm_arg(record)
    add_allow_out_of_scope_arg(record)
    record.add_argument(
        "--status",
        choices=("auto", "keep", "discard", "crash"),
        default="auto",
        help="Candidate result status.",
    )
    record.add_argument("--metric-value", type=float, help="Override the measured metric value.")
    record.add_argument("--description", default="", help="Short rationale for the result.")
    record.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    record.set_defaults(func=command_record)

    flow = subparsers.add_parser("flow", help="Show recorded metric flow for a run.")
    add_repo_arg(flow)
    flow.add_argument("--run-id", help="Run id. Defaults to the active run.")
    add_arm_arg(flow)
    flow.add_argument(
        "--width",
        type=int,
        default=28,
        help="Plot width for the ASCII metric chart.",
    )
    flow.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    flow.set_defaults(func=command_flow)

    preset_metric = subparsers.add_parser(
        "preset-metric",
        help="Run a metric preset against a repo-local script and print METRIC=<value>.",
    )
    add_repo_arg(preset_metric)
    preset_metric.add_argument(
        "--preset", required=True, choices=sorted(METRIC_PRESETS), help="Metric preset."
    )
    preset_metric.add_argument("--script", required=True, help="Repo-local script path.")
    preset_metric.set_defaults(func=command_preset_metric)

    monitor = subparsers.add_parser("monitor", help="Poll and report run progress at intervals.")
    add_repo_arg(monitor)
    monitor.add_argument("--run-id", help="Run id. Defaults to the active run.")
    monitor.add_argument("--interval", type=int, default=60, help="Check interval in seconds.")
    monitor.add_argument(
        "--output",
        choices=("terminal", "file"),
        default="terminal",
        help="Output destination.",
    )
    monitor.add_argument("--status-file", help="Path for file output mode.")
    add_interactive_arg(monitor)
    monitor.set_defaults(func=command_monitor)

    create = subparsers.add_parser(
        "create",
        help="Compare feature approaches, each tuned to its ceiling against a tuned control arm.",
    )
    add_repo_arg(create)
    create.add_argument("--part", help="Part id that the new feature relates to.")
    create.add_argument("--feature", help="Description of the feature to create.")
    create.add_argument(
        "--candidates", type=int, default=3, help="Number of candidate approaches (arms besides control)."
    )
    add_comparison_args(create, "Metric command to evaluate each arm.")
    create.set_defaults(func=command_create)

    delete = subparsers.add_parser(
        "delete",
        help="Compare deleting a part (then tuning) against a tuned control arm that keeps it.",
    )
    add_repo_arg(delete)
    delete.add_argument("--part", help="Part id to delete.")
    add_comparison_args(delete, "Metric command to evaluate each arm.")
    delete.set_defaults(func=command_delete)

    arm_ready = subparsers.add_parser(
        "arm-ready",
        help="Commit a comparison arm's setup and start tuning it.",
    )
    add_repo_arg(arm_ready)
    arm_ready.add_argument("--run-id", help="Comparison run id. Defaults to the active run.")
    arm_ready.add_argument("--arm", required=True, help="Arm id, e.g. approach-A or deleted.")
    arm_ready.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    arm_ready.set_defaults(func=command_arm_ready)

    compare = subparsers.add_parser(
        "compare",
        help="Compare the tuned ceilings of a create/delete run's arms.",
    )
    add_repo_arg(compare)
    compare.add_argument("--run-id", help="Comparison run id. Defaults to the active run.")
    compare.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    compare.set_defaults(func=command_compare)

    finalize = subparsers.add_parser(
        "finalize",
        help="Optionally merge the best candidate back, then remove the run's worktrees.",
    )
    add_repo_arg(finalize)
    finalize.add_argument("--run-id", help="Run id. Defaults to the active run.")
    finalize.add_argument(
        "--arm",
        help="For comparison runs: merge this arm's best instead of the compare winner.",
    )
    finalize.add_argument(
        "--merge",
        action="store_true",
        help="Squash-merge the best branch into the current checkout and leave it staged for review.",
    )
    finalize.add_argument(
        "--stop",
        action="store_true",
        help="Mark a still-running run as completed before finalizing it.",
    )
    finalize.add_argument(
        "--keep-best-worktree",
        action="store_true",
        help="Leave the best candidate's worktree in place.",
    )
    finalize.add_argument(
        "--prune-branches",
        action="store_true",
        help="Delete every run branch except the best one.",
    )
    finalize.add_argument(
        "--force",
        action="store_true",
        help="Remove worktrees even if they hold uncommitted or untracked files.",
    )
    finalize.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    finalize.set_defaults(func=command_finalize)

    return parser


def add_repo_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repo root or any path inside the repo.")


def add_arm_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--arm",
        help="For create/delete comparison runs: the arm whose tuning run to act on.",
    )


def add_allow_out_of_scope_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-out-of-scope",
        action="store_true",
        help="Accept a comparison-arm candidate that edits files outside the tuning scope (flagged in compare).",
    )


def add_comparison_args(parser: argparse.ArgumentParser, metric_command_help: str) -> None:
    parser.add_argument("--metric-command", help=metric_command_help)
    parser.add_argument("--metric", help="Metric name.")
    parser.add_argument("--metric-goal", choices=("minimize", "maximize"), help="Metric direction.")
    parser.add_argument(
        "--rounds", type=int, default=3, help="Tuning rounds per arm (every arm gets the same budget)."
    )
    parser.add_argument("--stop-rule", help="Per-arm stop rule: " + STOP_RULE_HELP + ".")
    parser.add_argument("--metric-timeout", type=float, help="Kill a metric command after this many seconds.")
    parser.add_argument(
        "--tune-scope",
        help=(
            "Comma-separated files and directories (trailing /) that tuning may change. Default: the "
            "target and its direct neighbours (create) or the deleted part's direct dependents (delete). "
            "Files changed during an arm's setup are always added."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(parser)


def add_interactive_arg(parser: argparse.ArgumentParser) -> None:
    """Add --interactive / --no-interactive flags with TTY-based default."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--interactive",
        action="store_true",
        default=None,
        help="Enable interactive wizard prompts.",
    )
    group.add_argument(
        "--no-interactive",
        action="store_true",
        default=False,
        help="Disable interactive prompts.",
    )


def resolve_interactive(args: argparse.Namespace) -> bool:
    """Resolve the interactive flag from args, defaulting to TTY detection."""
    if args.no_interactive:
        return False
    if args.interactive:
        return True
    return is_interactive_default()


def normalize_entry_argv(argv: list[str] | None) -> list[str] | None:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        return ["wizard"]
    first = argv[0]
    if first.startswith("-") or first in CLI_COMMANDS:
        return argv
    return ["wrap", first, *argv[1:]]


def group_parts_by_language(parts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group scanned parts by programming language."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for part in parts:
        groups[part.get("language", "unknown")].append(part)
    return dict(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def group_parts_by_directory(parts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group scanned parts by top-level directory (or '.' for root files)."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for part in parts:
        path = PurePosixPath(part["id"])
        top_dir = path.parts[0] if len(path.parts) > 1 else "."
        groups[top_dir].append(part)
    return dict(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def format_group_overview(
    groups: dict[str, list[dict[str, Any]]],
    *,
    directory_mode: bool = False,
    limit: int = 5,
) -> str:
    items = list(groups.items())[:limit]
    rendered = []
    for name, grouped_parts in items:
        label = f"{name}/" if directory_mode and name != "." else ("./" if directory_mode else name)
        rendered.append(f"{label} ({len(grouped_parts)})")
    if len(groups) > limit:
        rendered.append(f"... +{len(groups) - limit} more")
    return ", ".join(rendered)


def part_is_non_core(part: dict[str, Any]) -> bool:
    path = PurePosixPath(part["id"])
    segments = [segment.lower() for segment in path.parts]
    basename = path.name.lower()
    if any(segment in NON_CORE_PATH_HINTS for segment in segments):
        return True
    if basename in NON_CORE_FILE_HINTS:
        return True
    if basename.startswith("test_") or basename.endswith("_test.py"):
        return True
    if ".test." in basename or ".spec." in basename:
        return True
    return False


def core_focus_score(part: dict[str, Any]) -> int:
    path = PurePosixPath(part["id"])
    segments = [segment.lower() for segment in path.parts]
    basename = path.name.lower()
    dependencies = len(part.get("dependencies", []))
    dependents = len(part.get("dependents", []))
    signals = part.get("signals", [])

    score = 0
    if part.get("status") == "surely optimizable":
        score += 30
    else:
        score += 16
    if part.get("candidate_clarity"):
        score += 10
    if part.get("suggested_metric", {}).get("name") != "unknown":
        score += 8
    if part.get("dependency_clarity") == "clear":
        score += 4

    score += min(dependencies, 4) * 2
    score += min(dependents, 4) * 3
    score += min(len(signals), 3) * 2

    if dependencies and dependents:
        score += 4
    elif dependencies or dependents:
        score += 2
    else:
        score -= 5

    if any(segment in CORE_PATH_HINTS for segment in segments):
        score += 6
    if part_is_non_core(part):
        score -= 24

    return score


def select_scan_focus_parts(
    parts: list[dict[str, Any]],
    *,
    max_parts: int = DEFAULT_SCAN_FOCUS_PARTS,
    max_seeds: int = DEFAULT_SCAN_FOCUS_SEEDS,
) -> list[dict[str, Any]]:
    parts_by_id = {part["id"]: part for part in parts}
    ranked = sorted(
        parts,
        key=lambda item: (
            -core_focus_score(item),
            STATUS_ORDER.get(item.get("status"), 99),
            item["path"],
        ),
    )
    core_ranked = [part for part in ranked if not part_is_non_core(part)]

    seed_parts = [part for part in core_ranked if core_focus_score(part) >= 20][:max_seeds]
    if not seed_parts:
        seed_parts = core_ranked[:max_seeds]
    if not seed_parts:
        seed_parts = ranked[:max_seeds]

    selected_ids: list[str] = []

    def add_part(part_id: str) -> None:
        if part_id not in parts_by_id:
            return
        if part_id in selected_ids or len(selected_ids) >= max_parts:
            return
        selected_ids.append(part_id)

    for part in seed_parts:
        add_part(part["id"])
        for dependency in part.get("dependencies", []):
            add_part(dependency)
            if len(selected_ids) >= max_parts:
                break
        if len(selected_ids) >= max_parts:
            break
        for dependent in part.get("dependents", []):
            neighbor = parts_by_id.get(dependent)
            if neighbor and not part_is_non_core(neighbor):
                add_part(dependent)
            if len(selected_ids) >= max_parts:
                break
        if len(selected_ids) >= max_parts:
            break

    min_focus = min(max_parts, max(1, min(4, len(core_ranked) or len(ranked))))
    fill_source = core_ranked or ranked
    for part in fill_source:
        add_part(part["id"])
        if len(selected_ids) >= min_focus:
            break

    selected = [parts_by_id[part_id] for part_id in selected_ids]
    selected.sort(key=lambda item: (STATUS_ORDER.get(item["status"], 99), item["path"]))
    return selected


def format_scan_focus_line(part: dict[str, Any]) -> str:
    metric_name = part.get("suggested_metric", {}).get("name", "unknown")
    summary_bits = [f"metric={metric_name}"]
    summary_bits.append(f"deps={len(part.get('dependencies', []))}")
    summary_bits.append(f"dependents={len(part.get('dependents', []))}")
    return f"  - {part['id']} [{part['status']}; {', '.join(summary_bits)}]"


def print_scan_summary(
    parts: list[dict[str, Any]],
    lang_groups: dict[str, list[dict[str, Any]]],
    dir_groups: dict[str, list[dict[str, Any]]],
    focus_parts: list[dict[str, Any]],
    *,
    full_summary: bool,
) -> None:
    if full_summary:
        print("\nBy language:")
        for lang, lang_parts in lang_groups.items():
            ids = [p["id"] for p in lang_parts]
            print(f"  {lang} ({len(lang_parts)}): {', '.join(ids[:5])}"
                  + (f" ... +{len(ids)-5}" if len(ids) > 5 else ""))

        print("\nBy directory:")
        for directory, dir_parts in dir_groups.items():
            ids = [p["id"] for p in dir_parts]
            print(f"  {directory}/ ({len(dir_parts)}): {', '.join(ids[:5])}"
                  + (f" ... +{len(ids)-5}" if len(ids) > 5 else ""))

        print(f"\nModule dependency graph:\n{render_dependency_tree(parts)}\n")
        return

    print("\nRepo shape:")
    print(f"  languages: {format_group_overview(lang_groups)}")
    print(f"  top directories: {format_group_overview(dir_groups, directory_mode=True)}")

    print("\nCore functionality focus:")
    for part in focus_parts:
        print(format_scan_focus_line(part))

    print(f"\nFocused dependency graph:\n{render_dependency_tree(focus_parts, max_depth=2)}\n")
    if len(focus_parts) < len(parts):
        print(
            f"{len(parts) - len(focus_parts)} additional parts omitted from the default scan view. "
            "Use --full-summary to inspect all scanned parts."
        )


def sort_parts_for_selection(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        parts,
        key=lambda item: (
            -core_focus_score(item),
            STATUS_ORDER.get(item.get("status"), 99),
            item["path"],
        ),
    )


def dedupe_grouped_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for part in parts:
        if part["id"] in seen:
            continue
        seen.add(part["id"])
        result.append(part)
    return result


def functionality_label(metric_name: str) -> str:
    labels = {
        "latency_ms": "latency-sensitive functionality",
        "runtime_seconds": "runtime-heavy functionality",
        "throughput": "throughput-critical functionality",
        "memory_mb": "memory-sensitive functionality",
        "accuracy": "quality-sensitive functionality",
        "loss": "training-loss-sensitive functionality",
    }
    return labels.get(metric_name, metric_name.replace("_", " "))


def build_scan_group_selection(
    parts: list[dict[str, Any]],
    lang_groups: dict[str, list[dict[str, Any]]],
    dir_groups: dict[str, list[dict[str, Any]]],
    focus_parts: list[dict[str, Any]],
) -> tuple[list[str], dict[str, list[dict[str, Any]]], str]:
    group_options: list[str] = []
    group_map: dict[str, list[dict[str, Any]]] = {}
    default_group = "all scanned functionality"
    signature_keys: set[tuple[str, ...]] = set()
    ranked_parts = sort_parts_for_selection(parts)
    ranked_focus = sort_parts_for_selection(focus_parts)

    def add_group(label: str, grouped_parts: list[dict[str, Any]], *, default: bool = False) -> None:
        nonlocal default_group
        if not grouped_parts:
            return
        ordered = dedupe_grouped_parts(sort_parts_for_selection(grouped_parts))
        signature = tuple(part["id"] for part in ordered)
        if not signature or signature in signature_keys:
            return
        signature_keys.add(signature)
        group_options.append(label)
        group_map[label] = ordered
        if default:
            default_group = label

    add_group(
        f"best-defined optimization targets ({len(ranked_focus)} modules)",
        ranked_focus,
        default=True,
    )

    metric_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for part in ranked_parts:
        if part_is_non_core(part):
            continue
        metric_name = part.get("suggested_metric", {}).get("name")
        if metric_name and metric_name != "unknown":
            metric_groups[metric_name].append(part)

    for metric_name in ("latency_ms", "runtime_seconds", "throughput", "memory_mb", "accuracy", "loss"):
        grouped = metric_groups.get(metric_name, [])
        if grouped:
            add_group(
                f"{functionality_label(metric_name)} ({len(grouped)} modules)",
                grouped,
            )

    hubs = [
        part for part in ranked_parts
        if not part_is_non_core(part) and part.get("dependents")
    ]
    add_group(f"core dependency hubs ({len(hubs)} modules)", hubs)

    boundary_parts = [
        part for part in ranked_parts
        if not part_is_non_core(part)
        and part.get("dependencies")
        and not part.get("dependents")
    ]
    add_group(f"entry and execution paths ({len(boundary_parts)} modules)", boundary_parts)

    all_label = f"all scanned functionality ({len(parts)} modules)"
    add_group(all_label, ranked_parts)
    if default_group not in group_map:
        default_group = all_label
    return group_options, group_map, default_group


def interactive_select_part_from_scan(
    state: dict[str, Any],
    repo_root: Path,
    parts: list[dict[str, Any]],
    lang_groups: dict[str, list[dict[str, Any]]],
    dir_groups: dict[str, list[dict[str, Any]]],
    focus_parts: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(parts) == 1:
        chosen = parts[0]["id"]
        state.setdefault("selection", {})["part_id"] = chosen
        write_state(repo_root, state)
        print(f"selected: {chosen}")
        return parts[0]

    group_options, group_map, default_group = build_scan_group_selection(
        parts, lang_groups, dir_groups, focus_parts
    )
    chosen_group = wizard_select(
        "Which functionality area do you want to improve?",
        group_options,
        default=default_group,
    )
    filtered_parts = group_map[chosen_group]

    if chosen_group != default_group:
        print(f"\n{len(filtered_parts)} modules in scope.")
        print(f"\n{render_dependency_tree(filtered_parts)}\n")

    part_ids = [p["id"] for p in filtered_parts]
    chosen = wizard_select("Select a part to optimize", part_ids)
    state.setdefault("selection", {})["part_id"] = chosen
    write_state(repo_root, state)
    print(f"selected: {chosen}")
    return next(part for part in state["parts"] if part["id"] == chosen)


def render_dependency_tree(parts: list[dict[str, Any]], max_depth: int = 3) -> str:
    """Render a text-based module-level dependency graph for a set of parts."""
    part_ids = {p["id"] for p in parts}
    parts_by_id = {p["id"]: p for p in parts}
    lines: list[str] = []

    # Find root nodes: parts with no in-set dependents (nothing in the set depends on them)
    # or parts that have no in-set dependencies (top-level entry points)
    has_in_set_dependent = set()
    for part in parts:
        for dep in part.get("dependencies", []):
            if dep in part_ids:
                has_in_set_dependent.add(dep)

    roots = [p["id"] for p in parts if p["id"] not in has_in_set_dependent]
    if not roots:
        # Cycle — just pick all parts as roots
        roots = [p["id"] for p in parts]

    visited: set[str] = set()

    def _render(part_id: str, prefix: str, is_last: bool, depth: int) -> None:
        if depth > max_depth:
            return
        connector = "└── " if is_last else "├── "
        part = parts_by_id.get(part_id)
        dep_count = len(part.get("dependencies", [])) if part else 0
        dependent_count = len(part.get("dependents", [])) if part else 0
        lang = part.get("language", "?") if part else "?"
        suffix = f"  [{lang}, deps={dep_count}, dependents={dependent_count}]"
        if part_id in visited:
            lines.append(f"{prefix}{connector}{part_id}{suffix} (circular)")
            return
        lines.append(f"{prefix}{connector}{part_id}{suffix}")
        visited.add(part_id)

        if part:
            children = [d for d in part.get("dependencies", []) if d in part_ids]
            child_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(children):
                _render(child, child_prefix, i == len(children) - 1, depth + 1)

    for i, root in enumerate(roots):
        _render(root, "", i == len(roots) - 1, 0)

    return "\n".join(lines) if lines else "(no dependency edges found)"


def command_geo(args: argparse.Namespace) -> int:
    from autoresearch_wrapper import geo

    repo_root = detect_repo_root(Path(args.repo))
    config = geo.read_config((repo_root / args.config).resolve())
    if args.command == "geo-graph":
        result = geo.build_graph(repo_root, config)
    elif args.command == "geo-score":
        result = geo.readiness(repo_root, config)
        print(f"METRIC={result['score']}")
    elif args.command == "geo-compare":
        rows = geo.load_observations((repo_root / args.observations).resolve())
        result = geo.compare_platforms(config, rows, candidate=args.candidate)
    elif args.command == "geo-prioritize":
        evidence = geo.load_search_evidence((repo_root / args.search_evidence).resolve())
        result = geo.prioritize(config, evidence)
    elif args.command == "geo-explore":
        evidence = geo.load_search_evidence((repo_root / args.search_evidence).resolve())
        rows = geo.load_observations((repo_root / args.observations).resolve()) if args.observations else None
        result = geo.explore(repo_root, config, evidence, rows)
        if args.html_out:
            destination = (repo_root / args.html_out).resolve()
            if not destination.is_relative_to(repo_root):
                raise SystemExit("--html-out must be inside the repo")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(geo.render_explorer_html(result), encoding="utf-8")
    elif args.command == "geo-decide":
        evidence = geo.load_search_evidence((repo_root / args.search_evidence).resolve())
        result = geo.decide(config, evidence)
        if args.svg_out:
            destination = (repo_root / args.svg_out).resolve()
            if not destination.is_relative_to(repo_root):
                raise SystemExit("--svg-out must be inside the repo")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(geo.render_decision_svg(result), encoding="utf-8")
    elif args.command == "geo-apply":
        manifest = json.loads(Path(args.operations).read_text(encoding="utf-8"))
        if args.apply:
            git_dir = subprocess.run(
                ["git", "rev-parse", "--git-dir"], cwd=repo_root,
                capture_output=True, text=True, check=True,
            ).stdout.strip().replace("\\", "/")
            if "/worktrees/" not in git_dir:
                raise SystemExit("geo-apply --apply requires a Git worktree candidate")
        result = geo.apply_operations(repo_root, config, manifest["operations"],
                                      write=args.apply)
    else:
        raise SystemExit(f"unknown GEO command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_scan(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = refresh_repo_state(repo_root)
    write_state(repo_root, state)
    parts = state["parts"]
    print(f"scanned {len(parts)} parts into {state_file(repo_root)}")

    if not parts:
        return 0

    lang_groups = group_parts_by_language(parts)
    dir_groups = group_parts_by_directory(parts)
    focus_parts = select_scan_focus_parts(parts)
    print_scan_summary(parts, lang_groups, dir_groups, focus_parts, full_summary=args.full_summary)

    interactive = resolve_interactive(args)
    if not interactive or len(parts) < 2:
        return 0

    interactive_select_part_from_scan(state, repo_root, parts, lang_groups, dir_groups, focus_parts)
    return 0


def command_wizard(args: argparse.Namespace) -> int:
    if not resolve_interactive(args):
        raise SystemExit("wizard requires interactive mode; run it in a TTY or pass --interactive")

    repo_root = detect_repo_root(Path(args.repo))
    state = refresh_repo_state(repo_root)
    write_state(repo_root, state)
    parts = state["parts"]
    print(f"scanned {len(parts)} parts into {state_file(repo_root)}")
    if not parts:
        return 0

    lang_groups = group_parts_by_language(parts)
    dir_groups = group_parts_by_directory(parts)
    focus_parts = select_scan_focus_parts(parts)
    print_scan_summary(parts, lang_groups, dir_groups, focus_parts, full_summary=args.full_summary)

    part = interactive_select_part_from_scan(
        state, repo_root, parts, lang_groups, dir_groups, focus_parts
    )
    existing = dict(state.setdefault("part_configs", {}).get(part["id"], {}))
    metric = dict(existing.get("metric", {}))
    execution = dict(existing.get("execution", {}))

    suggested_metric = part.get("suggested_metric", {}).get("name")
    metric_name_default = metric.get("name")
    if not metric_name_default and suggested_metric and suggested_metric != "unknown":
        metric_name_default = suggested_metric
    metric_goal_default = (
        metric.get("goal")
        or infer_metric_goal(metric_name_default)
        or part.get("suggested_metric", {}).get("goal")
        or "minimize"
    )
    metric_command_default = metric.get("command")
    metric_regex = metric.get("regex") or DEFAULT_METRIC_REGEX
    mode_default = execution.get("mode") or "sequential"
    rounds_default = execution.get("rounds") or WRAP_DEFAULT_ROUNDS
    stop_rule_default = execution.get("stop_rule")
    parallelism_default = execution.get("parallelism")
    if mode_default in ("parallel", "wild") and not parallelism_default:
        parallelism_default = DEFAULT_PARALLELISM
    if mode_default not in ("parallel", "wild"):
        parallelism_default = 1
    early_exit_patience_default = execution.get("early_exit_patience")
    early_exit_threshold_default = execution.get("early_exit_threshold")
    wild_max_default = execution.get("wild_max_simultaneous") or 3

    print("\nSelected part details:")
    print(f"  part: {part['id']}")
    print(f"  status: {part['status']}")
    print(f"  suggested metric: {suggested_metric or 'unknown'}")
    print(f"  direct dependencies: {format_neighbors(part.get('dependencies', []))}")
    print(f"  dependents: {format_neighbors(part.get('dependents', []))}")
    blockers = dependency_run_blockers(part)
    if blockers:
        print(f"  dependency blockers: {', '.join(blockers)}")
    else:
        print("  dependency blockers: none")

    print("\nRun setup:")
    if not metric_name_default:
        print("  No metric could be inferred for this part. You need to provide one.")
    metric_name = wizard_input("Metric name", default=metric_name_default)
    metric_goal = wizard_select(
        "Metric goal",
        ["minimize", "maximize"],
        default=metric_goal_default,
    )
    print("  Metric command should print METRIC=<value> when evaluated.")
    metric_command = wizard_input("Metric command", default=metric_command_default)
    mode = wizard_select(
        "Execution mode",
        ["sequential", "parallel", "wild"],
        default=mode_default,
    )
    rounds = wizard_int("Rounds", default=rounds_default)
    parallelism = 1
    if mode in ("parallel", "wild"):
        parallelism = wizard_int(
            "Parallelism",
            default=parallelism_default or DEFAULT_PARALLELISM,
        )
    stop_rule = validate_stop_rule(wizard_optional_input("Stop rule", default=stop_rule_default))

    enable_early_exit = wizard_confirm(
        "Enable early exit?",
        default=bool(early_exit_patience_default),
    )
    early_exit_patience = None
    early_exit_threshold = None
    if enable_early_exit:
        early_exit_patience = wizard_int(
            "Early-exit patience",
            default=early_exit_patience_default or 3,
        )
        early_exit_threshold = wizard_optional_float(
            "Early-exit threshold",
            default=early_exit_threshold_default,
        )

    wild_max_simultaneous = None
    if mode == "wild":
        wild_max_simultaneous = wizard_int(
            "Wild max simultaneous changes",
            default=wild_max_default,
        )

    config = merge_config(
        part=part,
        existing=existing,
        metric_name=metric_name,
        metric_goal=metric_goal,
        metric_command=metric_command,
        metric_regex=metric_regex,
        mode=mode,
        rounds=rounds,
        stop_rule=stop_rule,
        parallelism=parallelism,
        entrypoint_type=existing.get("entrypoint", {}).get("type") or "part",
        entrypoint_path=existing.get("entrypoint", {}).get("path") or part["id"],
        metric_preset=metric.get("preset"),
        command_suggestion=metric.get("command_suggestion"),
        early_exit_patience=early_exit_patience,
        early_exit_threshold=early_exit_threshold,
        wild_max_simultaneous=wild_max_simultaneous,
    )
    normalize_execution_defaults(config["execution"])
    state.setdefault("part_configs", {})[part["id"]] = config
    state.setdefault("selection", {})["part_id"] = part["id"]
    refresh_part_readiness(state)
    write_state(repo_root, state)

    print("\nConfiguration saved:")
    print(f"  metric: {metric_name} ({metric_goal})")
    print(f"  mode: {mode}")
    print(f"  rounds: {rounds}")
    if mode in ("parallel", "wild"):
        print(f"  parallelism: {config['execution']['parallelism']}")
    if mode == "wild":
        print(f"  wild max simultaneous: {config['execution']['wild_max_simultaneous']}")
    if early_exit_patience is not None:
        print(f"  early exit patience: {early_exit_patience}")
        if early_exit_threshold is not None:
            print(f"  early exit threshold: {early_exit_threshold}")

    if blockers:
        print(
            "\nRun not started because the selected part still has dependency blockers. "
            "Clarify or narrow the target, then run `run`."
        )
        return 0

    if not wizard_confirm("Start the run now?", default=True):
        print("\nRun not started. Use `run` when you are ready.")
        return 0

    payload = start_or_resume_run(repo_root, state, part, config)
    print("\nRun started:")
    print(f"  run id: {payload['run_id']}")
    print(f"  part: {payload['part_id']}")
    print(f"  program: {payload['program_path']}")
    print(f"  candidates: {', '.join(payload['active_candidates'])}")
    return 0


def command_wrap(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = refresh_repo_state(repo_root)
    script_part = resolve_script_part(repo_root, state, args.script_path)
    existing = dict(state.setdefault("part_configs", {}).get(script_part["id"], {}))

    preset_name = args.metric_preset or infer_metric_preset(script_part)
    preset = METRIC_PRESETS[preset_name]
    suggested_command = build_preset_metric_command(repo_root, script_part["id"], preset_name)
    metric_command = args.metric_command or existing.get("metric", {}).get("command")
    if args.use_suggested_command:
        if not suggested_command:
            raise SystemExit("no suggested metric command available for this script path")
        metric_command = suggested_command

    config = merge_config(
        part=script_part,
        existing=existing,
        metric_name=preset["metric_name"],
        metric_goal=preset["goal"],
        metric_command=metric_command,
        metric_regex=existing.get("metric", {}).get("regex") or DEFAULT_METRIC_REGEX,
        mode=args.mode or existing.get("execution", {}).get("mode") or "sequential",
        rounds=args.rounds if args.rounds is not None else existing.get("execution", {}).get("rounds"),
        stop_rule=validate_stop_rule(args.stop_rule) or existing.get("execution", {}).get("stop_rule"),
        parallelism=(
            args.parallelism
            if args.parallelism is not None
            else existing.get("execution", {}).get("parallelism")
        ),
        entrypoint_type="script",
        entrypoint_path=script_part["id"],
        metric_preset=preset_name,
        command_suggestion=suggested_command,
    )
    normalize_execution_defaults(config["execution"])

    state.setdefault("part_configs", {})[script_part["id"]] = config
    state.setdefault("selection", {})["part_id"] = script_part["id"]
    refresh_part_readiness(state)
    write_state(repo_root, state)

    payload = {
        "part_id": script_part["id"],
        "metric_preset": preset_name,
        "suggested_metric": preset["metric_name"],
        "suggested_command": suggested_command,
        "ready": script_part.get("ready", False),
    }
    emit(payload, args.json)
    return 0


def command_configure(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    part = resolve_part(state, args.part)
    if part is None and args.part:
        part = register_explicit_part(repo_root, state, args.part)
    if part is None:
        raise SystemExit("unable to resolve part; run scan first or pass --part")

    existing = dict(state.setdefault("part_configs", {}).get(part["id"], {}))
    metric = dict(existing.get("metric", {}))
    execution = dict(existing.get("execution", {}))
    preset_name = args.metric_preset or metric.get("preset")
    preset = METRIC_PRESETS.get(preset_name) if preset_name else None
    command_suggestion = metric.get("command_suggestion")
    if preset_name:
        command_suggestion = build_preset_metric_command(repo_root, part["id"], preset_name)

    metric_name = (
        args.metric
        or metric.get("name")
        or (preset["metric_name"] if preset else None)
        or part["suggested_metric"]["name"]
    )
    metric_goal = (
        args.metric_goal
        or metric.get("goal")
        or (preset["goal"] if preset else None)
        or infer_metric_goal(metric_name)
        or part["suggested_metric"]["goal"]
        or "minimize"
    )
    metric_command = args.metric_command or metric.get("command")
    if args.use_suggested_command:
        if not command_suggestion:
            raise SystemExit("no suggested metric command is available for this part")
        metric_command = command_suggestion
    metric_regex = args.metric_regex or metric.get("regex") or DEFAULT_METRIC_REGEX
    mode = args.mode or execution.get("mode")
    rounds = args.rounds if args.rounds is not None else execution.get("rounds")
    stop_rule = validate_stop_rule(args.stop_rule) or execution.get("stop_rule")
    parallelism = (
        args.parallelism if args.parallelism is not None else execution.get("parallelism")
    )

    if args.interactive:
        metric_name = prompt_if_missing(metric_name, "Metric name")
        metric_goal = prompt_if_missing(metric_goal, "Metric goal [minimize|maximize]")
        metric_command = prompt_if_missing(metric_command, "Metric command")
        metric_regex = prompt_if_missing(metric_regex, "Metric regex")
        mode = prompt_if_missing(mode, "Mode [sequential|parallel|wild]")
        rounds = prompt_int_if_missing(rounds, "Rounds")
        stop_rule = stop_rule or validate_stop_rule(input(f"Stop rule (optional; {STOP_RULE_HELP}): "))
        if mode == "parallel" or mode == "wild":
            parallelism = prompt_int_if_missing(parallelism, "Parallelism")

    if mode == "parallel" and not parallelism:
        parallelism = 2
    if mode not in ("parallel", "wild"):
        parallelism = 1

    early_exit_patience = (
        args.early_exit_patience
        if args.early_exit_patience is not None
        else execution.get("early_exit_patience")
    )
    early_exit_threshold = (
        args.early_exit_threshold
        if args.early_exit_threshold is not None
        else execution.get("early_exit_threshold")
    )
    wild_max_simultaneous = (
        args.wild_max_simultaneous
        if args.wild_max_simultaneous is not None
        else execution.get("wild_max_simultaneous")
    )

    config = merge_config(
        part=part,
        existing=existing,
        metric_name=metric_name,
        metric_goal=metric_goal,
        metric_command=metric_command,
        metric_regex=metric_regex,
        mode=mode,
        rounds=rounds,
        stop_rule=stop_rule,
        parallelism=parallelism,
        entrypoint_type=existing.get("entrypoint", {}).get("type") or "part",
        entrypoint_path=existing.get("entrypoint", {}).get("path") or part["id"],
        metric_preset=preset_name,
        command_suggestion=command_suggestion,
        early_exit_patience=early_exit_patience,
        early_exit_threshold=early_exit_threshold,
        wild_max_simultaneous=wild_max_simultaneous,
        metric_timeout=args.metric_timeout,
    )
    normalize_execution_defaults(config["execution"])
    state.setdefault("part_configs", {})[part["id"]] = config
    state.setdefault("selection", {})["part_id"] = part["id"]
    refresh_part_readiness(state)
    write_state(repo_root, state)

    readiness = "ready" if part.get("ready") else "incomplete"
    print(f"configured {part['id']} ({readiness})")
    return 0


def command_status(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    refresh_run_worktrees(state)
    write_state(repo_root, state)
    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True))
    else:
        print(status_markdown(state))
    return 0


def start_or_resume_run(
    repo_root: Path,
    state: dict[str, Any],
    part: dict[str, Any],
    config: dict[str, Any] | None,
) -> dict[str, Any]:
    ensure_git_repo(repo_root)
    missing = missing_run_fields(config)
    if missing:
        raise SystemExit(
            "run config is incomplete: " + ", ".join(missing) + ". Configure the part first."
        )
    blockers = dependency_run_blockers(part)
    if blockers:
        raise SystemExit(
            "dependency graph is incomplete for selected part: "
            + ", ".join(blockers)
            + ". Re-scan or narrow the target before running."
        )

    run = find_active_run(state, part["id"])
    if run is None:
        warn_if_checkout_dirty(repo_root)
        run = create_run(repo_root, state, part, config)
    else:
        run["status"] = "running"
        run["resumed_at"] = now_iso()
        refresh_single_run_worktrees(run)

    state.setdefault("selection", {})["part_id"] = part["id"]
    state.setdefault("selection", {})["active_run_id"] = run["run_id"]
    write_state(repo_root, state)

    return {
        "run_id": run["run_id"],
        "part_id": part["id"],
        "program_path": run["program_path"],
        "active_candidates": [candidate["candidate_id"] for candidate in run["candidates"]],
    }


def command_run(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    with state_lock(repo_root):
        state = ensure_scanned(repo_root)
        part = resolve_part(state, args.part or state.get("selection", {}).get("part_id"))
        if part is None:
            raise SystemExit("no selected part; configure one with the wrapper first")
        config = state.get("part_configs", {}).get(part["id"])
        payload = start_or_resume_run(repo_root, state, part, config)
    emit(payload, args.json)
    return 0


def command_allocate(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    with state_lock(repo_root):
        state = ensure_scanned(repo_root)
        run = resolve_target_run(state, args.run_id, args.arm)
        if run.get("status") not in TERMINAL_RUN_STATUSES and (reason := stop_rule_reason(run)):
            run["status"] = "completed"
            run["stop_reason"] = reason
            refresh_parent_comparison(state, run)
            write_state(repo_root, state)
        if run.get("status") in TERMINAL_RUN_STATUSES:
            raise SystemExit(
                f"run {run['run_id']} is {run['status']} ({run.get('stop_reason') or 'no reason recorded'}); "
                "use `finalize` to merge the best candidate and clean up"
            )
        candidate = allocate_candidate(repo_root, run)
        write_state(repo_root, state)
    emit(candidate, args.json)
    return 0


def run_metric_settings(state: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Return the metric locked into the run, falling back to the part config for legacy runs."""
    metric = run.get("metric") or {}
    if metric.get("command"):
        return metric
    config = state.get("part_configs", {}).get(run["part_id"])
    if not config or not config.get("metric", {}).get("command"):
        raise SystemExit(f"run {run['run_id']} has no metric configuration")
    return config["metric"]


def command_evaluate(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    # Read without the lock: the metric command can run for a long time and
    # parallel candidates must be able to evaluate concurrently.
    state = load_state(repo_root)
    run = resolve_target_run(state, args.run_id, args.arm)
    candidate = get_candidate(run, args.candidate)
    if candidate is None:
        raise SystemExit(f"unknown candidate: {args.candidate}")

    metric = run_metric_settings(state, run)
    worktree_path = Path(candidate["worktree_path"])
    if not worktree_path.exists():
        raise SystemExit(f"candidate worktree is missing: {worktree_path}")

    # Snapshot the edits so the evaluated code is exactly what the branch holds;
    # later candidates are allocated from kept branches.
    commit = commit_worktree_changes(
        worktree_path, f"autoresearch: {run['run_id']} {candidate['candidate_id']}"
    )
    # Reject out-of-scope edits before spending compute on the metric.
    out_of_scope = out_of_scope_paths(run, worktree_path, commit)
    if out_of_scope and not args.allow_out_of_scope:
        raise SystemExit(scope_violation_message(candidate["candidate_id"], out_of_scope, run["tune_scope"]))
    result = run_metric_command(
        metric_command=metric["command"],
        metric_regex=metric["regex"],
        cwd=worktree_path,
        log_dir=Path(run["run_dir"]) / "logs",
        candidate_id=candidate["candidate_id"],
        timeout=args.timeout if args.timeout is not None else metric.get("timeout"),
    )
    result["commit"] = commit
    if out_of_scope:
        result["out_of_scope"] = out_of_scope

    with state_lock(repo_root):
        state = load_state(repo_root)
        run = resolve_run(state, run["run_id"])
        candidate = get_candidate(run, args.candidate)
        if candidate is None:
            raise SystemExit(f"candidate disappeared from state: {args.candidate}")
        candidate["latest_evaluation"] = result
        candidate["lifecycle"] = "evaluated" if result["exit_code"] == 0 else "failed"
        write_state(repo_root, state)
    emit(result, args.json)
    return 0


def command_record(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    with state_lock(repo_root):
        return record_locked(repo_root, args)


def resolve_recorded_commit(
    run: dict[str, Any], candidate: dict[str, Any], evaluation: dict[str, Any], manual_value: bool
) -> str | None:
    worktree_path = Path(candidate["worktree_path"])
    if not worktree_path.exists():
        return evaluation.get("commit")
    evaluated_commit = evaluation.get("commit")
    if manual_value or not evaluated_commit:
        # No evaluated snapshot to trust (manual metric or legacy evaluation): snapshot now.
        return commit_worktree_changes(
            worktree_path, f"autoresearch: {run['run_id']} {candidate['candidate_id']}"
        )
    head = current_commit(worktree_path)
    if head and head != evaluated_commit:
        raise SystemExit(
            f"{candidate['candidate_id']} HEAD moved since evaluate "
            f"({evaluated_commit[:12]} -> {head[:12]}); re-run evaluate before record"
        )
    return evaluated_commit


def record_locked(repo_root: Path, args: argparse.Namespace) -> int:
    state = ensure_scanned(repo_root)
    run = resolve_target_run(state, args.run_id, args.arm)
    candidate = get_candidate(run, args.candidate)
    if candidate is None:
        raise SystemExit(f"unknown candidate: {args.candidate}")
    if candidate.get("recorded"):
        raise SystemExit(
            f"{candidate['candidate_id']} is already recorded "
            f"({candidate.get('result', {}).get('status')}); allocate a new candidate instead"
        )

    metric = run_metric_settings(state, run)
    metric_name = metric["name"]
    goal = metric["goal"]
    evaluation = candidate.get("latest_evaluation", {})
    metric_value = args.metric_value if args.metric_value is not None else evaluation.get("metric_value")
    # `auto` on a failed or timed-out evaluation resolves to crash via decide_status.
    if metric_value is None and args.status != "crash" and not (args.status == "auto" and evaluation):
        raise SystemExit("no metric value available; run evaluate first or pass --metric-value")

    commit = resolve_recorded_commit(run, candidate, evaluation, args.metric_value is not None)

    # Backstop for manual metric values and edits that bypassed evaluate. Commits live in
    # the shared object store, so the diff works even if the worktree is gone.
    out_of_scope = out_of_scope_paths(run, repo_root, commit)
    accepted_at_evaluate = bool(evaluation.get("out_of_scope")) and evaluation.get("commit") == commit
    if out_of_scope and not (args.allow_out_of_scope or accepted_at_evaluate):
        raise SystemExit(scope_violation_message(candidate["candidate_id"], out_of_scope, run["tune_scope"]))

    chosen_status = args.status
    if chosen_status == "auto":
        chosen_status = decide_status(run, goal, metric_value)

    candidate["result"] = {
        "status": chosen_status,
        "description": args.description,
        "metric_value": metric_value,
        "commit": commit,
        "recorded_at": now_iso(),
    }
    if out_of_scope:
        candidate["result"]["out_of_scope"] = out_of_scope
    candidate["lifecycle"] = chosen_status
    candidate["recorded"] = True

    previous_best_metric = run.get("best_metric")

    if chosen_status == "keep" and metric_value is not None:
        # A manual keep may advance the base without being the best; best_* stays truthful.
        run["current_base_branch"] = candidate["branch"]
        if previous_best_metric is None or is_better_metric(metric_value, previous_best_metric, goal):
            run["best_metric"] = metric_value
            run["best_candidate_id"] = candidate["candidate_id"]

    if candidate["candidate_id"] != "seed":
        run["rounds_completed"] = count_completed_rounds(run)

    rounds_target = run["execution"].get("rounds")
    if run.get("status") in TERMINAL_RUN_STATUSES:
        # In-flight parallel candidates may still be recorded; don't reopen the run.
        pass
    elif rounds_target and run["rounds_completed"] >= rounds_target:
        run["status"] = "completed"
        run["stop_reason"] = f"rounds target reached ({rounds_target})"
    elif reason := stop_rule_reason(run):
        run["status"] = "completed"
        run["stop_reason"] = reason
    else:
        run["status"] = "running"

    # Early exit check
    early_exit = run.get("early_exit", {})
    if early_exit.get("patience") and run["status"] == "running":
        update_early_exit_state(run, metric_value, previous_best_metric)
        exit_check = check_early_exit(run)
        if exit_check["should_exit"]:
            run["status"] = "early_exit"
            run["stop_reason"] = exit_check["reason"]
            run["early_exit"]["triggered"] = True
            run["early_exit"]["trigger_reason"] = exit_check["reason"]

    append_result_row(run, candidate, metric_name, goal)
    refresh_parent_comparison(state, run)
    write_state(repo_root, state)
    emit(candidate["result"], args.json)
    return 0


def refresh_parent_comparison(state: dict[str, Any], run: dict[str, Any]) -> None:
    parent = state.get("runs", {}).get(run.get("parent_run_id") or "")
    if parent:
        refresh_comparison_status(state, parent)


def command_flow(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    run = resolve_target_run(state, args.run_id, args.arm)
    payload = metric_flow_snapshot(run)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(metric_flow_markdown(payload, width=args.width))
    return 0


def command_preset_metric(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    script_part = normalize_repo_relative_path(repo_root, args.script)
    script_abs = repo_root / script_part
    if not script_abs.exists():
        raise SystemExit(f"script path does not exist: {script_part}")

    runner = infer_script_runner(script_abs, script_part)
    if not runner:
        raise SystemExit(f"unable to infer how to run script: {script_part}")

    start = time.perf_counter()
    completed = subprocess.run(
        runner,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - start
    peak_rss_mb = child_peak_memory_mb()

    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        return completed.returncode

    metric_value = preset_metric_value(args.preset, elapsed, peak_rss_mb)
    print(f"METRIC={metric_value:.6f}")
    return 0


def detect_repo_root(start: Path) -> Path:
    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    try:
        output = git_stdout(candidate, ["rev-parse", "--show-toplevel"])
    except RuntimeError:
        return candidate
    return Path(output.strip()).resolve()


def refresh_repo_state(repo_root: Path) -> dict[str, Any]:
    state = load_state(repo_root)
    state["repo_root"] = str(repo_root)
    state["git"] = git_metadata(repo_root)
    parts, dependency_graph = discover_parts(repo_root)
    # Keep explicitly configured targets (e.g. non-code files) across rescans.
    discovered = {part["id"] for part in parts}
    for relative in state.get("explicit_parts", []):
        if relative not in discovered and (repo_root / relative).is_file():
            parts.append(explicit_part_record(relative))
    state["parts"] = parts
    state["dependency_graph"] = dependency_graph
    refresh_part_readiness(state)
    return state


def ensure_scanned(repo_root: Path) -> dict[str, Any]:
    state = load_state(repo_root)
    if not state.get("parts"):
        state = refresh_repo_state(repo_root)
        write_state(repo_root, state)
    return state


def load_state(repo_root: Path) -> dict[str, Any]:
    path = state_file(repo_root)
    if not path.exists():
        return default_state(repo_root)
    state = json.loads(path.read_text())
    return migrate_state(state, repo_root)


def migrate_state(state: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Migrate state from older schema versions to the current one."""
    version = state.get("schema_version", 1)
    if version < 2:
        for run in state.get("runs", {}).values():
            run.setdefault("run_type", "optimize")
            run.setdefault("early_exit", {
                "patience": None,
                "threshold": None,
                "rounds_without_improvement": 0,
                "triggered": False,
                "trigger_reason": None,
            })
            run.setdefault("create_info", None)
            run.setdefault("delete_info", None)
        for config in state.get("part_configs", {}).values():
            execution = config.get("execution", {})
            execution.setdefault("early_exit_patience", None)
            execution.setdefault("early_exit_threshold", None)
            execution.setdefault("wild_max_simultaneous", None)
        state["schema_version"] = 2
    # Keys from removed features (0.1.x): resource detection, the reference clone,
    # and the generated planning workspace.
    for key in ("resources", "reference", "planning_workspace"):
        state.pop(key, None)
    return state


def write_state(repo_root: Path, state: dict[str, Any]) -> None:
    target_dir = state_dir(repo_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not state.get("state_dir_excluded"):
        state["state_dir_excluded"] = exclude_state_dir_from_git(repo_root)
    state["updated_at"] = now_iso()
    atomic_write_text(state_file(repo_root), json.dumps(state, indent=2, sort_keys=True) + "\n")
    atomic_write_text(status_file(repo_root), status_markdown(state))


def exclude_state_dir_from_git(repo_root: Path) -> bool:
    """Keep the state dir out of `git status` via .git/info/exclude (local, never committed)."""
    completed = git_run(repo_root, ["rev-parse", "--git-path", "info/exclude"])
    if completed.returncode != 0:
        return False  # not a git repo (yet); try again on a later write
    exclude = Path(completed.stdout.strip())
    if not exclude.is_absolute():
        exclude = repo_root / exclude
    entry = f"/{STATE_DIRNAME}/"
    try:
        existing = exclude.read_text() if exclude.exists() else ""
        if entry not in existing.splitlines():
            exclude.parent.mkdir(parents=True, exist_ok=True)
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            exclude.write_text(f"{existing}{prefix}{entry}\n")
    except OSError:
        return False
    return True


def atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file + rename so readers never see a truncated file."""
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@contextlib.contextmanager
def state_lock(repo_root: Path):
    """Serialize read-modify-write cycles on state.json across processes.

    Uses a POSIX record lock when the filesystem supports it (NFS via lockd),
    and falls back to an atomic mkdir lock otherwise. Not reentrant: never nest.
    """
    target_dir = state_dir(repo_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    with (target_dir / STATE_LOCK_FILENAME).open("a") as handle:
        if try_posix_lock(handle):
            try:
                yield
            finally:
                fcntl.lockf(handle, fcntl.LOCK_UN)
            return
    with mkdir_lock(target_dir / f"{STATE_LOCK_FILENAME}.d"):
        yield


def try_posix_lock(handle: Any) -> bool:
    if fcntl is None:
        return False
    try:
        fcntl.lockf(handle, fcntl.LOCK_EX)
    except OSError:
        return False
    return True


@contextlib.contextmanager
def mkdir_lock(
    lock_dir: Path,
    timeout: float = STATE_LOCK_TIMEOUT_SECONDS,
    stale_after: float = STATE_LOCK_STALE_SECONDS,
):
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock_dir.mkdir()
            break
        except FileExistsError:
            try:
                age = time.time() - lock_dir.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > stale_after:
                # Holder most likely died; state writes are atomic, so reclaiming is safe.
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise SystemExit(f"timed out waiting for state lock: {lock_dir}")
            time.sleep(0.05)
    try:
        yield
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


def default_state(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "updated_at": now_iso(),
        "git": git_metadata(repo_root),
        "parts": [],
        "dependency_graph": {"edges": [], "unresolved_edges": []},
        "part_configs": {},
        "selection": {"part_id": None, "active_run_id": None},
        "runs": {},
    }


def normalize_repo_relative_path(repo_root: Path, raw_path: str) -> str:
    absolute = (repo_root / raw_path).resolve()
    try:
        return absolute.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise SystemExit(f"path must stay inside repo root: {raw_path}") from exc


def resolve_script_part(repo_root: Path, state: dict[str, Any], script_path: str) -> dict[str, Any]:
    relative = normalize_repo_relative_path(repo_root, script_path)
    absolute = repo_root / relative
    if not absolute.exists():
        raise SystemExit(f"script path does not exist: {relative}")
    part = resolve_part(state, relative)
    if part is None:
        raise SystemExit(
            f"script path is not a discovered repo part: {relative}. Use a supported source/script file."
        )
    return part


def infer_metric_preset(part: dict[str, Any]) -> str:
    metric_name = part.get("suggested_metric", {}).get("name")
    if metric_name in METRIC_PRESETS:
        return metric_name
    return "runtime_seconds"


def merge_config(
    *,
    part: dict[str, Any],
    existing: dict[str, Any],
    metric_name: str | None,
    metric_goal: str | None,
    metric_command: str | None,
    metric_regex: str | None,
    mode: str | None,
    rounds: int | None,
    stop_rule: str | None,
    parallelism: int | None,
    entrypoint_type: str,
    entrypoint_path: str,
    metric_preset: str | None,
    command_suggestion: str | None,
    early_exit_patience: int | None = None,
    early_exit_threshold: float | None = None,
    wild_max_simultaneous: int | None = None,
    metric_timeout: float | None = None,
) -> dict[str, Any]:
    if metric_timeout is None:
        metric_timeout = existing.get("metric", {}).get("timeout")
    return {
        "entrypoint": {
            "type": entrypoint_type,
            "path": entrypoint_path,
        },
        "metric": {
            "name": metric_name,
            "goal": metric_goal,
            "command": metric_command,
            "regex": metric_regex,
            "preset": metric_preset,
            "command_suggestion": command_suggestion,
            "timeout": metric_timeout,
        },
        "execution": {
            "mode": mode,
            "rounds": rounds,
            "stop_rule": stop_rule,
            "parallelism": parallelism,
            "early_exit_patience": early_exit_patience,
            "early_exit_threshold": early_exit_threshold,
            "wild_max_simultaneous": wild_max_simultaneous,
        },
        "updated_at": now_iso(),
    }


def normalize_execution_defaults(execution: dict[str, Any]) -> None:
    mode = execution.get("mode")
    if mode == "parallel" and not execution.get("parallelism"):
        execution["parallelism"] = 2
    if mode == "wild":
        if not execution.get("parallelism"):
            execution["parallelism"] = 2
        if not execution.get("wild_max_simultaneous"):
            execution["wild_max_simultaneous"] = 3
    if mode not in ("parallel", "wild"):
        execution["parallelism"] = 1


def build_preset_metric_command(repo_root: Path, script_path: str, preset_name: str) -> str | None:
    if preset_name not in METRIC_PRESETS:
        return None
    script_abs = repo_root / script_path
    if not script_abs.exists() or not infer_script_runner(script_abs, script_path):
        return None
    helper_python = shlex.quote(sys.executable)
    helper_script = shlex.quote(str(helper_script_path()))
    quoted_script = shlex.quote(script_path)
    quoted_preset = shlex.quote(preset_name)
    return (
        f"{helper_python} {helper_script} preset-metric "
        f"--preset {quoted_preset} --script {quoted_script}"
    )


def infer_script_runner(script_abs: Path, script_rel: str) -> list[str] | None:
    suffix = script_abs.suffix.lower()
    if suffix == ".py":
        return ["python3", script_rel]
    if suffix == ".sh":
        return ["bash", script_rel]
    if suffix in {".js", ".jsx"}:
        return ["node", script_rel]
    if suffix == ".rb":
        return ["ruby", script_rel]
    if suffix == ".php":
        return ["php", script_rel]

    shebang = read_shebang(script_abs)
    if "python" in shebang:
        return ["python3", script_rel]
    if any(shell in shebang for shell in ("bash", "sh")):
        return ["bash", script_rel]
    if "node" in shebang:
        return ["node", script_rel]
    if "ruby" in shebang:
        return ["ruby", script_rel]
    if "php" in shebang:
        return ["php", script_rel]
    if os.access(script_abs, os.X_OK):
        return [f"./{script_rel}" if not script_rel.startswith(".") else script_rel]
    return None


def read_shebang(path: Path) -> str:
    try:
        with path.open("r", errors="ignore") as handle:
            first_line = handle.readline().strip().lower()
    except OSError:
        return ""
    return first_line if first_line.startswith("#!") else ""


def child_peak_memory_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024


def preset_metric_value(preset_name: str, elapsed: float, peak_rss_mb: float) -> float:
    if preset_name == "runtime_seconds":
        return elapsed
    if preset_name == "latency_ms":
        return elapsed * 1000
    if preset_name == "throughput":
        return 0.0 if elapsed <= 0 else 1.0 / elapsed
    if preset_name == "memory_mb":
        return peak_rss_mb
    raise SystemExit(f"unsupported metric preset: {preset_name}")


def helper_script_path() -> Path:
    return Path(__file__).resolve().parent.parent / "scripts" / "autoresearch_wrapper.py"


def build_dependency_index(repo_root: Path, paths: list[Path]) -> dict[str, Any]:
    relative_paths = [path.relative_to(repo_root).as_posix() for path in paths]
    return {
        "repo_root": repo_root,
        "paths": set(relative_paths),
        "path_lookup": {relative_path: repo_root / relative_path for relative_path in relative_paths},
        "python_modules": build_python_module_map(relative_paths),
        "go_module": detect_go_module_name(repo_root),
    }


def build_python_module_map(relative_paths: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for relative_path in relative_paths:
        pure = PurePosixPath(relative_path)
        if pure.suffix != ".py":
            continue
        if pure.name == "__init__.py":
            module_parts = pure.parts[:-1]
        else:
            module_parts = (*pure.parts[:-1], pure.stem)
        candidates: list[tuple[str, ...]] = []
        if module_parts:
            candidates.append(tuple(module_parts))
            if module_parts[0] in {"src", "lib"} and len(module_parts) > 1:
                candidates.append(tuple(module_parts[1:]))
        for candidate_parts in candidates:
            module_name = ".".join(candidate_parts)
            if module_name and module_name not in mapping:
                mapping[module_name] = relative_path
    return mapping


def detect_go_module_name(repo_root: Path) -> str | None:
    go_mod = repo_root / "go.mod"
    if not go_mod.exists():
        return None
    for line in safe_read_text(go_mod, limit=4000).splitlines():
        match = re.match(r"\s*module\s+(\S+)", line)
        if match:
            return match.group(1)
    return None


def extract_dependencies(
    repo_root: Path,
    relative_path: str,
    text: str,
    language: str,
    index: dict[str, Any],
) -> dict[str, Any]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    kind = f"{language}-dependency"

    if language in {"html", "css", "svg", "robots", "sitemap", "markdown"}:
        for target in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^)'"\s]+)''', text, re.I):
            reference = next((value for value in target if value), "")
            if not reference or reference.startswith(("#", "http:", "https:", "data:")):
                continue
            reference = reference.split("?", 1)[0].split("#", 1)[0]
            candidate = (repo_root / relative_path).parent.joinpath(reference.lstrip("/")).resolve()
            if candidate.is_relative_to(repo_root) and candidate.is_file():
                resolved = candidate.relative_to(repo_root).as_posix()
                if resolved in index["paths"]:
                    dependencies.add(resolved)
        kind = "site-reference"
    elif language == "python":
        dependencies, unresolved = extract_python_dependencies(relative_path, text, index)
        kind = "python-import"
    elif language in {"javascript", "typescript"}:
        dependencies, unresolved = extract_js_dependencies(relative_path, text, language, index)
        kind = "js-import"
    elif language in {"c", "cpp", "objective-c", "objective-c++"}:
        dependencies, unresolved = extract_c_like_dependencies(relative_path, text, index)
        kind = "include"
    elif language == "shell":
        dependencies, unresolved = extract_shell_dependencies(relative_path, text, index)
        kind = "source"
    elif language == "php":
        dependencies, unresolved = extract_php_dependencies(relative_path, text, index)
        kind = "php-include"
    elif language == "ruby":
        dependencies, unresolved = extract_ruby_dependencies(relative_path, text, index)
        kind = "ruby-require"
    elif language == "go":
        dependencies, unresolved = extract_go_dependencies(relative_path, text, index)
        kind = "go-import"
    elif language == "rust":
        dependencies, unresolved = extract_rust_dependencies(relative_path, text, index)
        kind = "rust-module"
    elif language == "java":
        dependencies, unresolved = extract_java_dependencies(relative_path, text, index)
        kind = "java-import"

    return {
        "dependencies": sorted(dependencies),
        "unresolved": unresolved,
        "unresolved_important": [item for item in unresolved if item["important"]],
        "kind": kind,
    }


def extract_python_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return dependencies, unresolved

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved, unresolved_item = resolve_python_import(alias.name, relative_path, 0, index)
                if resolved:
                    dependencies.add(resolved)
                elif unresolved_item:
                    unresolved.append(unresolved_item)
        elif isinstance(node, ast.ImportFrom):
            base_resolved = None
            if node.module:
                base_resolved, unresolved_item = resolve_python_import(
                    node.module, relative_path, node.level, index
                )
                if base_resolved:
                    dependencies.add(base_resolved)
                elif unresolved_item:
                    unresolved.append(unresolved_item)
            for alias in node.names:
                if alias.name == "*":
                    continue
                if node.module and base_resolved:
                    combined = f"{node.module}.{alias.name}"
                    resolved, _ = resolve_python_import(combined, relative_path, node.level, index)
                    if resolved:
                        dependencies.add(resolved)
                    continue
                module_name = alias.name if not node.module else f"{node.module}.{alias.name}"
                resolved, unresolved_item = resolve_python_import(
                    module_name, relative_path, node.level, index
                )
                if resolved:
                    dependencies.add(resolved)
                elif unresolved_item and not node.module:
                    unresolved.append(unresolved_item)
    return dependencies, dedupe_unresolved(unresolved)


def resolve_python_import(
    module_name: str, relative_path: str, level: int, index: dict[str, Any]
) -> tuple[str | None, dict[str, Any] | None]:
    if level > 0:
        resolved = resolve_python_relative(module_name, relative_path, level, index)
        if resolved:
            return resolved, None
        return None, make_unresolved_dependency(
            module_name or ".",
            "python-relative-import",
            important=True,
            reason="relative import could not be resolved to a repo file",
        )

    resolved = resolve_python_absolute(module_name, index)
    if resolved:
        return resolved, None
    important = looks_like_local_python_module(module_name, index)
    return None, make_unresolved_dependency(
        module_name,
        "python-import",
        important=important,
        reason="import did not resolve to a repo-local Python module",
    )


def resolve_python_absolute(module_name: str, index: dict[str, Any]) -> str | None:
    mapping = index["python_modules"]
    if module_name in mapping:
        return mapping[module_name]
    candidate = module_name
    while "." in candidate:
        candidate = candidate.rsplit(".", 1)[0]
        if candidate in mapping:
            return mapping[candidate]
    return None


def resolve_python_relative(
    module_name: str, relative_path: str, level: int, index: dict[str, Any]
) -> str | None:
    base = PurePosixPath(relative_path).parent
    for _ in range(max(level - 1, 0)):
        base = base.parent
    module_segments = [segment for segment in module_name.split(".") if segment]
    candidates = resolve_python_fs_candidates(base, module_segments, index)
    return candidates[0] if candidates else None


def resolve_python_fs_candidates(
    base: PurePosixPath, module_segments: list[str], index: dict[str, Any]
) -> list[str]:
    if module_segments:
        target = base.joinpath(*module_segments)
        candidates = [target.with_suffix(".py").as_posix(), (target / "__init__.py").as_posix()]
    else:
        candidates = [(base / "__init__.py").as_posix()]
    return [candidate for candidate in candidates if candidate in index["paths"]]


def looks_like_local_python_module(module_name: str, index: dict[str, Any]) -> bool:
    top_level = module_name.split(".", 1)[0]
    for known_module in index["python_modules"]:
        if known_module == top_level or known_module.startswith(f"{top_level}."):
            return True
    return False


def extract_js_dependencies(
    relative_path: str, text: str, language: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    pattern = re.compile(
        r"""(?:import\s+(?:[^'"]+?\s+from\s+)?|export\s+[^'"]*?\s+from\s+|require\(|import\()\s*['"]([^'"]+)['"]""",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        specifier = match.group(1)
        if specifier.startswith(".") or specifier.startswith("/"):
            resolved = resolve_relative_module(relative_path, specifier, index, language)
            if resolved:
                dependencies.add(resolved)
            else:
                unresolved.append(
                    make_unresolved_dependency(
                        specifier,
                        "relative-import",
                        important=True,
                        reason="relative import could not be resolved to a repo file",
                    )
                )
    return dependencies, dedupe_unresolved(unresolved)


def extract_c_like_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for match in re.finditer(r'^\s*#include\s*([<"])([^">]+)[>"]', text, re.MULTILINE):
        opener, target = match.groups()
        if opener == '"':
            resolved = resolve_relative_module(relative_path, target, index, "c")
            if resolved:
                dependencies.add(resolved)
            else:
                unresolved.append(
                    make_unresolved_dependency(
                        target,
                        "quoted-include",
                        important=True,
                        reason="quoted include could not be resolved to a repo file",
                    )
                )
    return dependencies, dedupe_unresolved(unresolved)


def extract_shell_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for match in re.finditer(r'^\s*(?:source|\.)\s+([^\s#;]+)', text, re.MULTILINE):
        target = match.group(1).strip('"\'')
        if target.startswith("-"):
            continue
        resolved = resolve_relative_module(relative_path, target, index, "shell")
        if resolved:
            dependencies.add(resolved)
        else:
            unresolved.append(
                make_unresolved_dependency(
                    target,
                    "shell-source",
                    important=is_relative_like(target),
                    reason="sourced shell file could not be resolved to a repo file",
                )
            )
    return dependencies, dedupe_unresolved(unresolved)


def extract_php_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    pattern = re.compile(r"\b(?:require|require_once|include|include_once)\s*\(?\s*['\"]([^'\"]+)['\"]")
    for match in pattern.finditer(text):
        target = match.group(1)
        if is_relative_like(target):
            resolved = resolve_relative_module(relative_path, target, index, "php")
            if resolved:
                dependencies.add(resolved)
            else:
                unresolved.append(
                    make_unresolved_dependency(
                        target,
                        "php-include",
                        important=True,
                        reason="relative PHP include could not be resolved to a repo file",
                    )
                )
    return dependencies, dedupe_unresolved(unresolved)


def extract_ruby_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for match in re.finditer(r"\brequire_relative\s+['\"]([^'\"]+)['\"]", text):
        target = match.group(1)
        resolved = resolve_relative_module(relative_path, target, index, "ruby")
        if resolved:
            dependencies.add(resolved)
        else:
            unresolved.append(
                make_unresolved_dependency(
                    target,
                    "require_relative",
                    important=True,
                    reason="require_relative target could not be resolved to a repo file",
                )
            )
    return dependencies, dedupe_unresolved(unresolved)


def extract_go_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    module_name = index.get("go_module")
    if not module_name:
        return dependencies, unresolved
    for specifier in re.findall(r'^\s*"([^"]+)"', text, re.MULTILINE):
        if specifier == module_name or specifier.startswith(f"{module_name}/"):
            relative_package = specifier[len(module_name) :].lstrip("/")
            resolved = resolve_go_package(relative_package, index)
            if resolved:
                dependencies.update(resolved)
            else:
                unresolved.append(
                    make_unresolved_dependency(
                        specifier,
                        "go-import",
                        important=True,
                        reason="Go module import points inside repo but no package files were found",
                    )
                )
    return dependencies, dedupe_unresolved(unresolved)


def resolve_go_package(relative_package: str, index: dict[str, Any]) -> set[str]:
    package_dir = PurePosixPath(relative_package)
    matches = {
        relative_path
        for relative_path in index["paths"]
        if PurePosixPath(relative_path).suffix == ".go"
        and PurePosixPath(relative_path).parent == package_dir
    }
    return matches


def extract_rust_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    current_dir = PurePosixPath(relative_path).parent
    for match in re.finditer(r"^\s*mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", text, re.MULTILINE):
        module_name = match.group(1)
        resolved = resolve_rust_module(current_dir, module_name, index)
        if resolved:
            dependencies.add(resolved)
        else:
            unresolved.append(
                make_unresolved_dependency(
                    module_name,
                    "rust-mod",
                    important=True,
                    reason="Rust mod declaration could not be resolved to a repo file",
                )
            )
    return dependencies, dedupe_unresolved(unresolved)


def resolve_rust_module(current_dir: PurePosixPath, module_name: str, index: dict[str, Any]) -> str | None:
    candidates = [
        (current_dir / f"{module_name}.rs").as_posix(),
        (current_dir / module_name / "mod.rs").as_posix(),
    ]
    for candidate in candidates:
        if candidate in index["paths"]:
            return candidate
    return None


def extract_java_dependencies(
    relative_path: str, text: str, index: dict[str, Any]
) -> tuple[set[str], list[dict[str, Any]]]:
    dependencies: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    for match in re.finditer(r"^\s*import\s+([a-zA-Z0-9_.]+);", text, re.MULTILINE):
        specifier = match.group(1)
        resolved = resolve_java_import(specifier, index)
        if resolved:
            dependencies.add(resolved)
    return dependencies, unresolved


def resolve_java_import(specifier: str, index: dict[str, Any]) -> str | None:
    suffix = PurePosixPath(*specifier.split(".")).with_suffix(".java").as_posix()
    for candidate in index["paths"]:
        if candidate.endswith(suffix):
            return candidate
    return None


def resolve_relative_module(
    relative_path: str, specifier: str, index: dict[str, Any], language: str
) -> str | None:
    current_dir = PurePosixPath(relative_path).parent
    candidate_base = PurePosixPath(
        normalize_posix_path((current_dir / specifier).as_posix())
    )
    extensions = language_extensions(language)
    candidates: list[str] = []
    if candidate_base.as_posix() in index["paths"]:
        candidates.append(candidate_base.as_posix())
    if candidate_base.suffix:
        candidates.append(candidate_base.as_posix())
    else:
        for extension in extensions:
            candidates.append(candidate_base.with_suffix(extension).as_posix())
        for extension in extensions:
            candidates.append((candidate_base / f"index{extension}").as_posix())
        for extension in (".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".php", ".rb", ".h"):
            candidates.append(candidate_base.with_suffix(extension).as_posix())
    for candidate in candidates:
        if candidate in index["paths"]:
            return candidate
    return None


def language_extensions(language: str) -> tuple[str, ...]:
    if language == "typescript":
        return (".ts", ".tsx", ".js", ".jsx")
    if language == "javascript":
        return (".js", ".jsx", ".ts", ".tsx")
    if language == "php":
        return (".php",)
    if language == "ruby":
        return (".rb",)
    if language == "shell":
        return (".sh",)
    if language in {"c", "cpp", "objective-c", "objective-c++"}:
        return (".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".m", ".mm")
    return (".py",)


def normalize_posix_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    return "." if normalized == "." else normalized


def is_relative_like(target: str) -> bool:
    return target.startswith(".") or "/" in target


def dedupe_unresolved(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item["kind"], item["target"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def make_unresolved_dependency(
    target: str, kind: str, important: bool, reason: str
) -> dict[str, Any]:
    return {
        "target": target,
        "kind": kind,
        "important": important,
        "reason": reason,
    }


def classify_dependency_clarity(dependency_info: dict[str, Any]) -> str:
    if dependency_info["unresolved_important"]:
        return "partial"
    return "clear"


def summarize_neighbors(dependencies: list[str], dependents: list[str], limit: int = 4) -> list[str]:
    neighbors = []
    for candidate in dependencies + dependents:
        if candidate not in neighbors:
            neighbors.append(candidate)
        if len(neighbors) >= limit:
            break
    return neighbors


def build_dependency_summary(part: dict[str, Any]) -> dict[str, Any]:
    unresolved = part.get("unresolved_dependencies", [])
    important_unresolved = [item for item in unresolved if item.get("important")]
    return {
        "direct_dependencies": len(part.get("dependencies", [])),
        "dependents": len(part.get("dependents", [])),
        "key_neighbors": part.get("key_neighbors", []),
        "unresolved_count": len(important_unresolved),
        "important_dependencies_known": not dependency_run_blockers(part),
    }


def merge_part_notes(base_notes: str, dependency_summary: dict[str, Any]) -> str:
    summary_note = (
        f"deps={dependency_summary['direct_dependencies']}, "
        f"dependents={dependency_summary['dependents']}, "
        f"important_unresolved={dependency_summary['unresolved_count']}"
    )
    return f"{base_notes}; {summary_note}"


def explicit_part_record(relative: str) -> dict[str, Any]:
    """A part the user named directly: any repo file, including non-code (.md, .yml, .html)."""
    part = {
        "id": relative,
        "path": relative,
        "language": infer_file_language(Path(relative)) or "other",
        "status": "probably optimizable",
        "explicit": True,
        "suggested_metric": {"name": "unknown", "goal": None},
        "candidate_clarity": False,
        "signals": [],
        "dependencies": [],
        "dependents": [],
        "unresolved_dependencies": [],
        "dependency_clarity": "clear",
        "key_neighbors": [],
        "notes": "explicit target (not discovered by scan); no dependency graph",
    }
    part["dependency_summary"] = build_dependency_summary(part)
    return part


def register_explicit_part(repo_root: Path, state: dict[str, Any], raw_path: str) -> dict[str, Any] | None:
    relative = normalize_repo_relative_path(repo_root, raw_path)
    if not (repo_root / relative).is_file():
        return None
    explicit = state.setdefault("explicit_parts", [])
    if relative not in explicit:
        explicit.append(relative)
    part = explicit_part_record(relative)
    state.setdefault("parts", []).append(part)
    return part


def dependency_run_blockers(part: dict[str, Any]) -> list[str]:
    blockers = []
    for unresolved in part.get("unresolved_dependencies", []):
        if unresolved.get("important"):
            blockers.append(unresolved["target"])
    return blockers


def format_neighbors(neighbors: list[str], fallback: str = "none", limit: int = 4) -> str:
    if not neighbors:
        return fallback
    rendered = ", ".join(f"`{neighbor}`" for neighbor in neighbors[:limit])
    if len(neighbors) > limit:
        rendered += ", ..."
    return rendered


def discover_parts(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    docs = load_doc_corpus(repo_root)
    paths = list(iter_source_files(repo_root))
    index = build_dependency_index(repo_root, paths)
    parts: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    unresolved_edges: list[dict[str, Any]] = []
    dependents_map: dict[str, set[str]] = defaultdict(set)

    for path in paths:
        text = safe_read_text(path)
        if not text:
            continue
        relative = path.relative_to(repo_root).as_posix()
        language = infer_file_language(path) or "shell"
        dependency_info = extract_dependencies(repo_root, relative, text, language, index)
        suggested_metric = infer_metric(relative, text, docs)
        candidate_clarity, signals = candidate_space(relative, text)
        dependency_clarity = classify_dependency_clarity(dependency_info)
        status = (
            "surely optimizable"
            if candidate_clarity
            and suggested_metric["name"] != "unknown"
            and dependency_clarity == "clear"
            else "probably optimizable"
        )
        notes = []
        if signals:
            notes.append("signals: " + ", ".join(signals[:3]))
        if suggested_metric["name"] == "unknown":
            notes.append("metric unclear")
        else:
            notes.append(f"suggested metric: {suggested_metric['name']}")
        if dependency_info["unresolved_important"]:
            notes.append(
                "dependency boundary unclear: "
                + ", ".join(item["target"] for item in dependency_info["unresolved_important"][:3])
            )
        else:
            notes.append(
                "direct deps: "
                f"{len(dependency_info['dependencies'])}, important unresolved: 0"
            )
        parts.append(
            {
                "id": relative,
                "path": relative,
                "language": language,
                "status": status,
                "suggested_metric": suggested_metric,
                "candidate_clarity": candidate_clarity,
                "signals": signals,
                "dependencies": dependency_info["dependencies"],
                "dependents": [],
                "unresolved_dependencies": dependency_info["unresolved"],
                "dependency_clarity": dependency_clarity,
                "dependency_summary": {},
                "key_neighbors": [],
                "notes": "; ".join(notes),
            }
        )
        for dependency in dependency_info["dependencies"]:
            edges.append(
                {
                    "from": relative,
                    "to": dependency,
                    "kind": dependency_info["kind"],
                    "confidence": "high",
                }
            )
            dependents_map[dependency].add(relative)
        for unresolved in dependency_info["unresolved"]:
            unresolved_edges.append(
                {
                    "from": relative,
                    "target": unresolved["target"],
                    "kind": unresolved["kind"],
                    "important": unresolved["important"],
                    "reason": unresolved["reason"],
                }
            )

    part_by_id = {part["id"]: part for part in parts}
    for part in parts:
        part["dependents"] = sorted(dependents_map.get(part["id"], set()))
        part["key_neighbors"] = summarize_neighbors(part["dependencies"], part["dependents"])
        part["dependency_summary"] = build_dependency_summary(part)
        part["notes"] = merge_part_notes(part["notes"], part["dependency_summary"])

    parts.sort(key=lambda item: (STATUS_ORDER.get(item["status"], 99), item["path"]))
    return parts, {
        "generated_at": now_iso(),
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"])),
        "unresolved_edges": sorted(
            unresolved_edges, key=lambda item: (item["from"], item["target"])
        ),
    }


def load_doc_corpus(repo_root: Path) -> str:
    chunks: list[str] = []
    total = 0
    for path in iter_text_docs(repo_root):
        text = safe_read_text(path, limit=24000)
        if not text:
            continue
        chunks.append(text.lower())
        total += len(text)
        if total >= 120000:
            break
    return "\n".join(chunks)


def iter_source_files(repo_root: Path):
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        for filename in files:
            path = Path(root) / filename
            if infer_file_language(path):
                yield path


def infer_file_language(path: Path) -> str | None:
    if path.name.lower() == "readme.md":
        return "markdown"
    if path.name == "robots.txt":
        return "robots"
    if path.name == "sitemap.xml":
        return "sitemap"
    suffix_language = SOURCE_EXTENSIONS.get(path.suffix.lower())
    if suffix_language:
        return suffix_language
    shebang = read_shebang(path)
    if "python" in shebang:
        return "python"
    if any(shell in shebang for shell in ("bash", "sh")):
        return "shell"
    if "node" in shebang:
        return "javascript"
    if "ruby" in shebang:
        return "ruby"
    if "php" in shebang:
        return "php"
    return None


def iter_text_docs(repo_root: Path):
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        for filename in files:
            lowered = filename.lower()
            if lowered.startswith("readme") or lowered.endswith((".md", ".rst", ".txt")):
                yield Path(root) / filename


def safe_read_text(path: Path, limit: int = 32000) -> str:
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return ""
    return text[:limit]


def infer_metric(relative_path: str, text: str, docs: str) -> dict[str, Any]:
    lowered_path = relative_path.lower()
    lowered_text = text.lower()
    local_combined = "\n".join([lowered_path, lowered_text])
    local_scores: dict[str, int] = {}
    doc_scores: dict[str, int] = {}

    for metric_name, tokens in PATH_HINTS.items():
        for token in tokens:
            if hint_present(lowered_path, token):
                local_scores[metric_name] = local_scores.get(metric_name, 0) + 2

    for metric_name, tokens in TEXT_HINTS.items():
        for token in tokens:
            if hint_present(local_combined, token):
                local_scores[metric_name] = local_scores.get(metric_name, 0) + 1
            elif hint_present(docs, token):
                doc_scores[metric_name] = doc_scores.get(metric_name, 0) + 1

    if not local_scores:
        return {"name": "unknown", "goal": None, "source": "unknown"}

    scores = dict(local_scores)
    for metric_name, value in doc_scores.items():
        scores[metric_name] = scores.get(metric_name, 0) + value

    metric_name = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "name": metric_name,
        "goal": infer_metric_goal(metric_name),
        "source": "inferred-local" if metric_name in local_scores else "inferred-local+docs",
    }


def candidate_space(relative_path: str, text: str) -> tuple[bool, list[str]]:
    lowered = f"{relative_path.lower()}\n{text.lower()}"
    signals = [keyword for keyword in OPTIMIZATION_KEYWORDS if keyword in lowered]
    return bool(signals), signals


def infer_metric_goal(metric_name: str | None) -> str | None:
    if not metric_name or metric_name == "unknown":
        return None
    return "maximize" if metric_name in MAXIMIZE_METRICS else "minimize"


def hint_present(text: str, token: str) -> bool:
    if re.fullmatch(r"[a-z0-9_+-]+", token):
        return re.search(rf"\b{re.escape(token)}\b", text) is not None
    return token in text


def refresh_part_readiness(state: dict[str, Any]) -> None:
    configs = state.get("part_configs", {})
    selected_part_id = state.get("selection", {}).get("part_id")
    for part in state.get("parts", []):
        config = configs.get(part["id"])
        part["configured"] = bool(config)
        part["dependency_ready"] = not dependency_run_blockers(part)
        part["ready"] = part_config_ready(config) and part["dependency_ready"]
        part["selected"] = part["id"] == selected_part_id


def part_config_ready(config: dict[str, Any] | None) -> bool:
    return bool(config) and not missing_run_fields(config)


def missing_run_fields(config: dict[str, Any] | None) -> list[str]:
    if not config:
        return ["metric", "execution"]
    missing: list[str] = []
    metric = config.get("metric", {})
    execution = config.get("execution", {})
    if not metric.get("name"):
        missing.append("metric.name")
    if not metric.get("goal"):
        missing.append("metric.goal")
    if not metric.get("command"):
        missing.append("metric.command")
    if not metric.get("regex"):
        missing.append("metric.regex")
    if not execution.get("mode"):
        missing.append("execution.mode")
    # A legacy free-text stop rule is never enforced, so it cannot stand in for rounds.
    if not (execution.get("rounds") or stop_rule_is_enforceable(execution.get("stop_rule"))):
        missing.append("execution.rounds_or_stop_rule")
    return missing


# ---------------------------------------------------------------------------
# Stop rules
# ---------------------------------------------------------------------------

STOP_RULE_HELP = (
    "comma-separated clauses, any of which ends the run: "
    "metric<=X | metric>=X | metric<X | metric>X (best metric so far), "
    "stalled:N (N rounds in a row without improvement), minutes:N (wall clock since run start)"
)
STOP_CLAUSE_RE = re.compile(
    r"^(?:metric\s*(?P<op><=|>=|<|>)\s*(?P<threshold>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"|(?P<kind>stalled|minutes)\s*:\s*(?P<count>\d+(?:\.\d+)?))$"
)


def parse_stop_rule(text: str | None) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    for raw in re.split(r"[,;]", text or ""):
        raw = raw.strip()
        if not raw:
            continue
        match = STOP_CLAUSE_RE.match(raw)
        if not match:
            raise ValueError(f"unrecognized stop rule clause {raw!r}")
        if match.group("op"):
            clauses.append(
                {"kind": "metric", "op": match.group("op"), "value": float(match.group("threshold"))}
            )
        else:
            clauses.append({"kind": match.group("kind"), "value": float(match.group("count"))})
    return clauses


def validate_stop_rule(text: str | None) -> str | None:
    """Return the normalized rule (None when empty) or exit with the supported grammar."""
    if text is None or not text.strip():
        return None
    try:
        parse_stop_rule(text)
    except ValueError as exc:
        raise SystemExit(f"invalid stop rule: {exc}; expected {STOP_RULE_HELP}") from exc
    return text.strip()


def stop_rule_is_enforceable(text: str | None) -> bool:
    try:
        return bool(parse_stop_rule(text))
    except ValueError:
        return False


def trailing_stalled_rounds(run: dict[str, Any]) -> int:
    """Consecutive most-recent recordings that did not beat the best before them."""
    goal = run.get("metric", {}).get("goal")
    recorded = sorted(
        (candidate for candidate in run.get("candidates", []) if candidate.get("recorded")),
        key=lambda candidate: candidate.get("result", {}).get("recorded_at") or "",
    )
    best: float | None = None
    stalled = 0
    for index, candidate in enumerate(recorded):
        value = candidate["result"].get("metric_value")
        if candidate["result"].get("status") != "crash" and value is not None and (
            best is None or is_better_metric(value, best, goal)
        ):
            best = value
            stalled = 0
        elif index > 0:
            stalled += 1
    return stalled


def stop_rule_reason(run: dict[str, Any], now: dt.datetime | None = None) -> str | None:
    try:
        clauses = parse_stop_rule(run.get("execution", {}).get("stop_rule"))
    except ValueError:
        return None
    best = run.get("best_metric")
    for clause in clauses:
        if clause["kind"] == "metric":
            if best is None:
                continue
            op, threshold = clause["op"], clause["value"]
            reached = {
                "<=": best <= threshold,
                ">=": best >= threshold,
                "<": best < threshold,
                ">": best > threshold,
            }[op]
            if reached:
                return f"stop rule: best metric {format_metric_value(best)} {op} {threshold:g}"
        elif clause["kind"] == "stalled":
            stalled = trailing_stalled_rounds(run)
            if stalled >= clause["value"]:
                return f"stop rule: {stalled} rounds without improvement"
        elif clause["kind"] == "minutes":
            created = dt.datetime.fromisoformat(run["created_at"])
            elapsed = ((now or dt.datetime.now(dt.timezone.utc)) - created).total_seconds() / 60
            if elapsed >= clause["value"]:
                return f"stop rule: {elapsed:.1f} minutes elapsed (limit {clause['value']:g})"
    return None


def resolve_part(state: dict[str, Any], part_id: str | None) -> dict[str, Any] | None:
    parts = state.get("parts", [])
    if not parts:
        return None
    if part_id:
        for part in parts:
            if part["id"] == part_id or part["path"] == part_id:
                return part
        return None  # explicit part_id given but not found
    selected = state.get("selection", {}).get("part_id")
    if selected:
        for part in parts:
            if part["id"] == selected:
                return part
    return parts[0] if len(parts) == 1 else None


def state_dir(repo_root: Path) -> Path:
    return repo_root / STATE_DIRNAME


def state_file(repo_root: Path) -> Path:
    return state_dir(repo_root) / STATE_FILENAME


def status_file(repo_root: Path) -> Path:
    return state_dir(repo_root) / STATUS_FILENAME


def runs_dir(repo_root: Path) -> Path:
    return state_dir(repo_root) / RUNS_DIRNAME


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def status_markdown(state: dict[str, Any]) -> str:
    lines = [
        "# Autoresearch Wrapper Status",
        "",
        f"- Updated: {state.get('updated_at')}",
        f"- Repo root: `{state.get('repo_root')}`",
        f"- Git available: `{state.get('git', {}).get('available')}`",
        f"- Git worktree support: `{state.get('git', {}).get('worktrees')}`",
        "",
        "## Selected Part",
    ]

    selected = state.get("selection", {}).get("part_id")
    active_run_id = state.get("selection", {}).get("active_run_id")
    lines.append(f"- Part: `{selected}`" if selected else "- Part: none selected")
    lines.append(f"- Active run: `{active_run_id}`" if active_run_id else "- Active run: none")
    if selected:
        selected_part = next((part for part in state.get("parts", []) if part["id"] == selected), None)
        selected_config = state.get("part_configs", {}).get(selected, {})
        if selected_part:
            lines.append(
                f"- Direct dependencies: {format_neighbors(selected_part.get('dependencies', []))}"
            )
            lines.append(
                f"- Dependents: {format_neighbors(selected_part.get('dependents', []))}"
            )
            entrypoint = selected_config.get("entrypoint", {})
            metric = selected_config.get("metric", {})
            if entrypoint.get("type"):
                lines.append(f"- Entrypoint type: `{entrypoint.get('type')}`")
            if metric.get("preset"):
                lines.append(f"- Metric preset: `{metric.get('preset')}`")
            if metric.get("command_suggestion") and not metric.get("command"):
                lines.append(f"- Suggested metric command: `{metric.get('command_suggestion')}`")
            blockers = dependency_run_blockers(selected_part)
            if blockers:
                lines.append(f"- Dependency blockers: {', '.join(blockers)}")

    lines.extend(
        [
            "",
            "## Parts",
            "",
            "| Part | Status | Suggested Metric | Ready | Dependency Clarity | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for part in state.get("parts", []):
        lines.append(
            "| {part} | {status} | {metric} | {ready} | {clarity} | {notes} |".format(
                part=part["id"],
                status=part["status"],
                metric=part["suggested_metric"]["name"],
                ready="yes" if part.get("ready") else "no",
                clarity=part.get("dependency_clarity", "unknown"),
                notes=part.get("notes", "").replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Dependency Table",
            "",
            "| Part | Direct Deps | Dependents | Key Neighbors | Clarity | Unresolved |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for part in state.get("parts", []):
        unresolved = [item for item in part.get("unresolved_dependencies", []) if item.get("important")]
        unresolved_display = (
            ", ".join(item["target"] for item in unresolved[:3]) if unresolved else "-"
        )
        lines.append(
            "| {part} | {deps} | {dependents} | {neighbors} | {clarity} | {unresolved} |".format(
                part=part["id"],
                deps=len(part.get("dependencies", [])),
                dependents=len(part.get("dependents", [])),
                neighbors=format_neighbors(part.get("key_neighbors", []), fallback="-"),
                clarity=part.get("dependency_clarity", "unknown"),
                unresolved=unresolved_display.replace("|", "/"),
            )
        )

    lines.extend(["", "## Runs", ""])
    if not state.get("runs"):
        lines.append("- No runs initialized.")
        return "\n".join(lines) + "\n"

    for run_id, run in sorted(state["runs"].items()):
        flow = metric_flow_snapshot(run)
        lines.append(
            "- `{run_id}`: `{status}`, part `{part}`, rounds `{done}/{target}`, best `{best}`".format(
                run_id=run_id,
                status=run.get("status"),
                part=run.get("part_id"),
                done=run.get("rounds_completed", 0),
                target=run.get("execution", {}).get("rounds") or "-",
                best=run.get("best_metric"),
            )
        )
        for candidate in run.get("candidates", []):
            marker = "missing" if candidate.get("missing") else candidate.get("lifecycle")
            lines.append(
                "  - `{cid}`: `{life}`, `{path}`".format(
                    cid=candidate["candidate_id"],
                    life=marker,
                    path=candidate["worktree_path"],
                )
            )
        for arm in run.get("arms", []):
            tuning = f", tuning run `{arm['child_run_id']}`" if arm.get("child_run_id") else ""
            lines.append(f"  - arm `{arm['arm_id']}` ({arm['kind']}): `{arm['phase']}`{tuning}")
        if flow["points"]:
            lines.append(f"  - Metric flow: {flow['sequence']}")
            lines.append(f"  - Best-so-far: {flow['best_sequence']}")
    return "\n".join(lines) + "\n"


def metric_flow_snapshot(run: dict[str, Any]) -> dict[str, Any]:
    points = load_metric_flow_points(run)
    metric = run.get("metric", {})
    numeric_points = [point for point in points if point["metric_value"] is not None]
    best_point = None
    if numeric_points:
        best_value = min(
            point["metric_value"] for point in numeric_points
        ) if metric.get("goal") != "maximize" else max(
            point["metric_value"] for point in numeric_points
        )
        best_point = next(
            point for point in numeric_points if point["metric_value"] == best_value
        )

    return {
        "run_id": run.get("run_id"),
        "part_id": run.get("part_id"),
        "metric_name": metric.get("name"),
        "goal": metric.get("goal"),
        "results_path": run.get("results_path"),
        "points": points,
        "best_metric": best_point["metric_value"] if best_point else None,
        "best_candidate_id": best_point["candidate_id"] if best_point else None,
        "latest_metric": points[-1]["metric_value"] if points else None,
        "latest_candidate_id": points[-1]["candidate_id"] if points else None,
        "sequence": format_metric_flow_sequence(points, "metric_value"),
        "best_sequence": format_metric_flow_sequence(points, "best_so_far"),
    }


def load_metric_flow_points(run: dict[str, Any]) -> list[dict[str, Any]]:
    results_path = Path(run["results_path"])
    if not results_path.exists():
        return []
    points: list[dict[str, Any]] = []
    with results_path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for index, row in enumerate(reader, start=1):
            metric_value = parse_optional_float(row.get("metric_value"))
            point = {
                "step": index,
                "timestamp": row.get("timestamp"),
                "candidate_id": row.get("candidate_id"),
                "status": row.get("status"),
                "metric_name": row.get("metric_name"),
                "metric_value": metric_value,
                "goal": row.get("goal"),
                "description": row.get("description") or "",
                "best_so_far": None,
                "delta_from_previous": None,
            }
            if points and metric_value is not None and points[-1]["metric_value"] is not None:
                point["delta_from_previous"] = metric_value - points[-1]["metric_value"]
            points.append(point)

    best_so_far: float | None = None
    goal = run.get("metric", {}).get("goal") or (points[0]["goal"] if points else "minimize")
    for point in points:
        value = point["metric_value"]
        if value is not None and is_better_metric(value, best_so_far, goal):
            best_so_far = value
        point["best_so_far"] = best_so_far
    return points


def parse_optional_float(value: str | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def is_better_metric(value: float, current_best: float | None, goal: str | None) -> bool:
    if current_best is None:
        return True
    if goal == "maximize":
        return value > current_best
    return value < current_best


def format_metric_value(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.6f}"


def format_metric_delta(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.6f}"


def format_metric_flow_sequence(points: list[dict[str, Any]], key: str, limit: int = 8) -> str:
    if not points:
        return "none recorded"
    sequence = [
        f"{point['candidate_id']}={format_metric_value(point.get(key))}" for point in points[:limit]
    ]
    if len(points) > limit:
        sequence.append("...")
    return " -> ".join(sequence)


def metric_flow_markdown(snapshot: dict[str, Any], width: int = 28) -> str:
    lines = [
        f"# Metric Flow: {snapshot['run_id']}",
        "",
        f"- Part: `{snapshot['part_id']}`",
        f"- Metric: `{snapshot['metric_name']}`",
        f"- Goal: `{snapshot['goal']}`",
        f"- Results path: `{snapshot['results_path']}`",
    ]

    if not snapshot["points"]:
        lines.append("- No recorded metric values yet.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            f"- Best: `{format_metric_value(snapshot['best_metric'])}` (`{snapshot['best_candidate_id']}`)",
            f"- Latest: `{format_metric_value(snapshot['latest_metric'])}` (`{snapshot['latest_candidate_id']}`)",
            "",
            "## Flow",
            "",
            f"- Sequence: {snapshot['sequence']}",
            f"- Best so far: {snapshot['best_sequence']}",
            "",
            "## Sequence Table",
            "",
            "| Step | Candidate | Status | Metric | Delta | Best So Far | Description |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for point in snapshot["points"]:
        lines.append(
            "| {step} | {candidate} | {status} | {metric} | {delta} | {best} | {description} |".format(
                step=point["step"],
                candidate=point["candidate_id"],
                status=point["status"],
                metric=format_metric_value(point["metric_value"]),
                delta=format_metric_delta(point["delta_from_previous"]),
                best=format_metric_value(point["best_so_far"]),
                description=point["description"].replace("|", "/"),
            )
        )

    lines.extend(["", "## Plot", "", "```text"])
    lines.extend(metric_plot_lines(snapshot["points"], width=width))
    lines.extend(["```", ""])
    return "\n".join(lines)


def metric_plot_lines(points: list[dict[str, Any]], width: int = 28) -> list[str]:
    width = max(width, 8)
    numeric_values = [point["metric_value"] for point in points if point["metric_value"] is not None]
    if not numeric_values:
        return ["(no numeric metric values recorded)"]

    minimum = min(numeric_values)
    maximum = max(numeric_values)
    span = maximum - minimum
    lines: list[str] = []
    for point in points:
        value = point["metric_value"]
        marker = "*" if value is not None and value == point["best_so_far"] else " "
        if value is None:
            bar = "?" * max(1, width // 4)
            lines.append(f"{marker} {point['candidate_id']:<14} | {bar:<{width}} -")
            continue
        bar_length = width if span == 0 else max(1, int(round(((value - minimum) / span) * (width - 1))) + 1)
        bar = "#" * bar_length
        lines.append(
            f"{marker} {point['candidate_id']:<14} | {bar:<{width}} {format_metric_value(value)}"
        )
    return lines


def git_metadata(repo_root: Path) -> dict[str, Any]:
    metadata = {"available": False, "root": str(repo_root), "worktrees": False}
    if shutil.which("git") is None:
        metadata["reason"] = "git not found"
        return metadata
    try:
        inside = git_stdout(repo_root, ["rev-parse", "--is-inside-work-tree"])
    except RuntimeError as exc:
        metadata["reason"] = str(exc)
        return metadata
    if inside.strip() != "true":
        metadata["reason"] = "not inside a git worktree"
        return metadata
    metadata["available"] = True
    metadata["root"] = git_stdout(repo_root, ["rev-parse", "--show-toplevel"]).strip()
    try:
        metadata["head"] = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()
    except RuntimeError:
        metadata["head"] = None
    try:
        git_stdout(repo_root, ["worktree", "list"])
    except RuntimeError as exc:
        metadata["reason"] = str(exc)
        return metadata
    metadata["worktrees"] = True
    return metadata


def ensure_git_repo(repo_root: Path) -> None:
    metadata = git_metadata(repo_root)
    if not metadata.get("available"):
        raise SystemExit("git repo required: " + metadata.get("reason", "unknown error"))
    if not metadata.get("worktrees"):
        raise SystemExit("git worktree support required for run initialization")


def git_stdout(cwd: Path, args: list[str]) -> str:
    completed = git_run(cwd, args, check=True)
    return completed.stdout


def git_run(cwd: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git not found") from exc
    if check and completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(stderr or f"git {' '.join(args)} failed")
    return completed


TERMINAL_RUN_STATUSES = {"completed", "early_exit"}
RESULTS_HEADER = (
    "timestamp\trun_id\tcandidate_id\tstatus\tmetric_name\tmetric_value\tgoal\tcommit\tbranch\tworktree\tdescription\n"
)


def find_active_run(state: dict[str, Any], part_id: str) -> dict[str, Any] | None:
    """Find the resumable optimize run for a part; create/delete runs are never resumed by `run`."""

    def resumable(run: dict[str, Any] | None) -> bool:
        return bool(
            run
            and run.get("part_id") == part_id
            and run.get("run_type", "optimize") == "optimize"
            and not run.get("parent_run_id")  # comparison arms are driven via --arm
            and run.get("status") not in TERMINAL_RUN_STATUSES
        )

    active_id = state.get("selection", {}).get("active_run_id")
    if active_id:
        run = state.get("runs", {}).get(active_id)
        if resumable(run):
            return run
    for run in state.get("runs", {}).values():
        if resumable(run):
            return run
    return None


def resolve_run(state: dict[str, Any], run_id: str | None) -> dict[str, Any]:
    resolved_run_id = run_id or state.get("selection", {}).get("active_run_id")
    if not resolved_run_id:
        raise SystemExit("no run selected; initialize one with `run` first")
    run = state.get("runs", {}).get(resolved_run_id)
    if run is None:
        raise SystemExit(f"unknown run: {resolved_run_id}")
    refresh_single_run_worktrees(run)
    return run


def create_run(
    repo_root: Path, state: dict[str, Any], part: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    run_id = build_run_id(part["id"], state, repo_root)
    worktree_root = default_worktree_root(repo_root) / run_id
    base_ref = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()
    seed = create_candidate_worktree(
        repo_root=repo_root,
        worktree_path=worktree_root / "seed",
        branch_name=f"autoresearch/{slugify(part['id'])}/{run_id}/seed",
        base_ref=base_ref,
        candidate_id="seed",
        based_on=base_ref,
    )
    run = init_optimize_run(
        repo_root, part, config, run_id=run_id, worktree_root=worktree_root, seed=seed, base_ref=base_ref
    )
    state.setdefault("runs", {})[run_id] = run
    state.setdefault("selection", {})["active_run_id"] = run_id
    return run


def init_optimize_run(
    repo_root: Path,
    part: dict[str, Any],
    config: dict[str, Any],
    *,
    run_id: str,
    worktree_root: Path,
    seed: dict[str, Any],
    base_ref: str,
) -> dict[str, Any]:
    """Build an optimize run around an existing seed worktree (fresh, or a comparison arm's setup)."""
    run_dir = runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    worktree_root.mkdir(parents=True, exist_ok=True)

    run = {
        "run_id": run_id,
        "part_id": part["id"],
        "run_type": "optimize",
        "status": "running",
        "created_at": now_iso(),
        "run_dir": str(run_dir),
        "program_path": str(run_dir / "program.md"),
        "results_path": str(run_dir / "results.tsv"),
        "worktree_root": str(worktree_root),
        "base_ref": base_ref,
        "current_base_branch": seed["branch"],
        "best_candidate_id": None,
        "best_metric": None,
        "execution": config["execution"],
        "metric": config["metric"],
        "rounds_completed": 0,
        "candidates": [seed],
        "early_exit": {
            "patience": config["execution"].get("early_exit_patience"),
            "threshold": config["execution"].get("early_exit_threshold"),
            "rounds_without_improvement": 0,
            "triggered": False,
            "trigger_reason": None,
        },
        "create_info": None,
        "delete_info": None,
    }

    Path(run["results_path"]).write_text(RESULTS_HEADER)
    Path(run["program_path"]).write_text(render_program(repo_root, run, part, config))

    if config["execution"].get("mode") in ("parallel", "wild"):
        parallelism = max(int(config["execution"].get("parallelism", 2)), 1)
        for _ in range(parallelism):
            allocate_candidate(repo_root, run)
    return run


def build_run_id(part_id: str, state: dict[str, Any], repo_root: Path) -> str:
    """Timestamped id, made unique: two runs for one part can start within the same second."""
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"{timestamp}-{slugify(part_id)}"
    taken = set(state.get("runs", {}))
    run_id, suffix = base, 2
    while run_id in taken or (runs_dir(repo_root) / run_id).exists():
        run_id, suffix = f"{base}-{suffix}", suffix + 1
    return run_id


def slugify(value: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:limit] or "part"


def default_worktree_root(repo_root: Path) -> Path:
    return repo_root.parent / f"{repo_root.name}.autoresearch-worktrees"


def create_candidate_worktree(
    repo_root: Path,
    worktree_path: Path,
    branch_name: str,
    base_ref: str,
    candidate_id: str,
    based_on: str,
) -> dict[str, Any]:
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    git_run(
        repo_root,
        ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref],
        check=True,
    )
    return {
        "candidate_id": candidate_id,
        "branch": branch_name,
        "worktree_path": str(worktree_path),
        "based_on": based_on,
        "created_at": now_iso(),
        "lifecycle": "allocated" if candidate_id != "seed" else "seed",
        "missing": False,
    }


def allocate_candidate(repo_root: Path, run: dict[str, Any]) -> dict[str, Any]:
    worktree_root = Path(run["worktree_root"])
    existing = {
        candidate["candidate_id"]
        for candidate in run["candidates"]
        if candidate["candidate_id"] != "seed"
    }
    next_index = 1
    while f"candidate-{next_index:03d}" in existing:
        next_index += 1
    candidate_id = f"candidate-{next_index:03d}"
    branch_name = f"autoresearch/{slugify(run['part_id'])}/{run['run_id']}/{candidate_id}"
    candidate = create_candidate_worktree(
        repo_root=repo_root,
        worktree_path=worktree_root / candidate_id,
        branch_name=branch_name,
        base_ref=run["current_base_branch"],
        candidate_id=candidate_id,
        based_on=run["current_base_branch"],
    )
    run["candidates"].append(candidate)
    return candidate


def get_candidate(run: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    for candidate in run.get("candidates", []):
        if candidate["candidate_id"] == candidate_id:
            return candidate
    return None


def run_metric_command(
    metric_command: str,
    metric_regex: str,
    cwd: Path,
    log_dir: Path,
    candidate_id: str,
    timeout: float | None = None,
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    # Own process group so a timeout kills the whole command tree, not just the shell.
    process = subprocess.Popen(
        metric_command,
        cwd=cwd,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    combined = stdout + ("\n" if stdout and stderr else "") + stderr
    metric_value = None if timed_out else parse_metric_value(combined, metric_regex)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{candidate_id}-{timestamp}.log"
    log_lines = [f"$ {metric_command}", "", stdout, "", stderr]
    if timed_out:
        log_lines.append(f"\n[autoresearch-wrapper] killed after {timeout}s timeout")
    log_path.write_text("\n".join(log_lines))
    return {
        "command": metric_command,
        "regex": metric_regex,
        "exit_code": None if timed_out else process.returncode,
        "timed_out": timed_out,
        "metric_value": metric_value,
        "log_path": str(log_path),
        "recorded_at": now_iso(),
    }


def parse_metric_value(output: str, metric_regex: str) -> float | None:
    # Use the last match: scripts often print intermediate values before the final one.
    match = None
    for match in re.finditer(metric_regex, output, re.MULTILINE):
        pass
    if not match:
        return None
    if "value" in match.groupdict():
        value = match.group("value")
    else:
        value = match.group(1)
    return float(value)


def decide_status(run: dict[str, Any], goal: str, metric_value: float | None) -> str:
    if metric_value is None:
        return "crash"
    best_metric = run.get("best_metric")
    if best_metric is None:
        return "keep"
    if goal == "maximize":
        return "keep" if metric_value > best_metric else "discard"
    return "keep" if metric_value < best_metric else "discard"


def count_completed_rounds(run: dict[str, Any]) -> int:
    return sum(
        1
        for candidate in run.get("candidates", [])
        if candidate["candidate_id"] != "seed"
        and candidate.get("result", {}).get("status") in {"keep", "discard", "crash"}
    )


def append_result_row(run: dict[str, Any], candidate: dict[str, Any], metric_name: str, goal: str) -> None:
    result = candidate.get("result", {})
    commit = result.get("commit") or current_commit(Path(candidate["worktree_path"]))
    row = [
        now_iso(),
        run["run_id"],
        candidate["candidate_id"],
        result.get("status"),
        metric_name,
        str(result.get("metric_value")),
        goal,
        commit or "",
        candidate["branch"],
        candidate["worktree_path"],
        result.get("description", "").replace("\t", " "),
    ]
    with Path(run["results_path"]).open("a") as handle:
        handle.write("\t".join(row) + "\n")


def warn_if_checkout_dirty(repo_root: Path) -> None:
    """New runs start from HEAD; say so when tracked changes would be left out."""
    output = git_run(repo_root, ["status", "--porcelain", "--untracked-files=no"]).stdout
    # Porcelain lines are "XY path"; don't strip the output, X may be a space.
    files = [line[3:] for line in output.splitlines() if line.strip()]
    if not files:
        return
    head = git_stdout(repo_root, ["rev-parse", "--short", "HEAD"]).strip()
    shown = ", ".join(files[:5]) + (f", and {len(files) - 5} more" if len(files) > 5 else "")
    print(
        f"warning: the main checkout has uncommitted changes ({shown}). This run starts from "
        f"HEAD ({head}) and does not include them; commit them first if they belong in the baseline.",
        file=sys.stderr,
    )


def git_identity_args(cwd: Path) -> list[str]:
    """Fallback committer identity so snapshots work where git user.* is unset."""
    args: list[str] = []
    if not git_run(cwd, ["config", "user.name"]).stdout.strip():
        args += ["-c", "user.name=autoresearch-wrapper"]
    if not git_run(cwd, ["config", "user.email"]).stdout.strip():
        args += ["-c", "user.email=autoresearch-wrapper@localhost"]
    return args


def commit_worktree_changes(worktree_path: Path, message: str) -> str:
    """Commit all pending changes (respecting .gitignore) and return HEAD."""
    git_run(worktree_path, ["add", "-A"], check=True)
    staged = git_run(worktree_path, ["diff", "--cached", "--quiet"])
    if staged.returncode == 1:
        git_run(
            worktree_path,
            [*git_identity_args(worktree_path), "commit", "--no-verify", "-m", message],
            check=True,
        )
    elif staged.returncode != 0:
        raise RuntimeError(staged.stderr.strip() or "git diff --cached failed")
    return git_stdout(worktree_path, ["rev-parse", "HEAD"]).strip()


def current_commit(worktree_path: Path) -> str | None:
    try:
        return git_stdout(worktree_path, ["rev-parse", "HEAD"]).strip()
    except RuntimeError:
        return None


def render_program(
    repo_root: Path,
    run: dict[str, Any],
    part: dict[str, Any],
    config: dict[str, Any],
) -> str:
    template_path = Path(__file__).resolve().parent.parent / "templates" / "autoresearch_program_template.md"
    template = Template(template_path.read_text())
    execution = config["execution"]
    metric = config["metric"]
    return template.substitute(
        run_id=run["run_id"],
        repo_root=str(repo_root),
        part_id=part["id"],
        status=part["status"],
        suggested_metric=part["suggested_metric"]["name"],
        metric_preset=metric.get("preset") or "none",
        metric_name=metric["name"],
        metric_goal=metric["goal"],
        metric_command=metric["command"],
        metric_regex=metric["regex"],
        execution_mode=execution["mode"],
        rounds=execution.get("rounds"),
        stop_rule=execution.get("stop_rule") or "none",
        parallelism=execution.get("parallelism"),
        state_json=str(state_file(repo_root)),
        status_md=str(status_file(repo_root)),
        run_dir=run["run_dir"],
        seed_worktree=run["candidates"][0]["worktree_path"],
        direct_dependencies=format_neighbors(part.get("dependencies", [])),
        dependents=format_neighbors(part.get("dependents", [])),
        unresolved_dependencies=format_neighbors(
            [item["target"] for item in part.get("unresolved_dependencies", [])],
            fallback="none",
        ),
        script_path=str(helper_script_path()),
    )


def is_interactive_default() -> bool:
    """Return True if stdin is a TTY, enabling wizard mode by default."""
    return sys.stdin.isatty()


def wizard_select(label: str, options: list[str], default: str | None = None) -> str:
    """Display numbered options and return the user's choice."""
    print(f"\n{label}:")
    for i, option in enumerate(options, 1):
        marker = " *" if option == default else ""
        print(f"  {i}. {option}{marker}")
    if default:
        prompt = f"Choice [default: {default}]: "
    else:
        prompt = "Choice: "
    while True:
        raw = input(prompt).strip()
        if not raw and default:
            return default
        try:
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1]
        except ValueError:
            if raw in options:
                return raw
        print(f"  Please enter a number between 1 and {len(options)}.")


def wizard_confirm(label: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"{label} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def wizard_input(label: str, default: str | None = None) -> str:
    """Prompt for free text input."""
    if default:
        raw = input(f"{label} [default: {default}]: ").strip()
        return raw or default
    while True:
        raw = input(f"{label}: ").strip()
        if raw:
            return raw
        print("  A value is required.")


def wizard_int(label: str, default: int | None = None) -> int:
    """Prompt for an integer."""
    while True:
        if default is not None:
            raw = input(f"{label} [default: {default}]: ").strip()
            if not raw:
                return default
        else:
            raw = input(f"{label}: ").strip()
        try:
            return int(raw)
        except ValueError:
            print("  Please enter a valid integer.")


def wizard_optional_input(label: str, default: str | None = None) -> str | None:
    """Prompt for optional text input; blank keeps the default or leaves it unset."""
    if default:
        raw = input(f"{label} [default: {default}]: ").strip()
        return default if not raw else raw
    raw = input(f"{label} [optional]: ").strip()
    return raw or None


def wizard_optional_int(label: str, default: int | None = None) -> int | None:
    """Prompt for an optional integer; blank keeps the default or leaves it unset."""
    while True:
        if default is not None:
            raw = input(f"{label} [default: {default}]: ").strip()
            if not raw:
                return default
        else:
            raw = input(f"{label} [optional]: ").strip()
            if not raw:
                return None
        try:
            return int(raw)
        except ValueError:
            print("  Please enter a valid integer.")


def wizard_optional_float(label: str, default: float | None = None) -> float | None:
    """Prompt for an optional float; blank keeps the default or leaves it unset."""
    while True:
        if default is not None:
            raw = input(f"{label} [default: {default}]: ").strip()
            if not raw:
                return default
        else:
            raw = input(f"{label} [optional]: ").strip()
            if not raw:
                return None
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a valid number.")


def prompt_if_missing(current: Any, label: str) -> Any:
    if current:
        return current
    return wizard_input(label)


def prompt_int_if_missing(current: int | None, label: str) -> int:
    if current is not None:
        return current
    return wizard_int(label)


def emit(payload: Any, as_json: bool) -> None:
    if isinstance(payload, dict) or as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)


def refresh_run_worktrees(state: dict[str, Any]) -> None:
    for run in state.get("runs", {}).values():
        refresh_single_run_worktrees(run)


def refresh_single_run_worktrees(run: dict[str, Any]) -> None:
    for candidate in run.get("candidates", []):
        candidate["missing"] = not Path(candidate["worktree_path"]).exists()


# ---------------------------------------------------------------------------
# Feature: Early Exit
# ---------------------------------------------------------------------------


def update_early_exit_state(run: dict[str, Any], metric_value: float | None, previous_best: float | None = None) -> None:
    """Update the early exit tracking state after a new metric is recorded."""
    early_exit = run.get("early_exit", {})
    if not early_exit.get("patience"):
        return
    # previous_best is the best *before* this record; None means this is the first
    # measurement (the baseline), which can never be a stall.
    best_metric = previous_best
    threshold = early_exit.get("threshold") or 0.0
    goal = run.get("metric", {}).get("goal") or "minimize"

    if metric_value is None:
        # A crashed or timed-out candidate is a round without improvement.
        early_exit["rounds_without_improvement"] = early_exit.get("rounds_without_improvement", 0) + 1
        return
    if best_metric is None:
        return

    improved = False
    if goal == "maximize":
        improved = metric_value > best_metric + threshold
    else:
        improved = metric_value < best_metric - threshold

    if improved:
        early_exit["rounds_without_improvement"] = 0
    else:
        early_exit["rounds_without_improvement"] = early_exit.get("rounds_without_improvement", 0) + 1


def check_early_exit(run: dict[str, Any]) -> dict[str, Any]:
    """Check whether early exit criteria are met."""
    early_exit = run.get("early_exit", {})
    patience = early_exit.get("patience")
    if not patience:
        return {"should_exit": False, "reason": None}
    stalled = early_exit.get("rounds_without_improvement", 0)
    if stalled >= patience:
        return {
            "should_exit": True,
            "reason": f"no improvement for {stalled} rounds (patience={patience})",
        }
    return {"should_exit": False, "reason": None}


# ---------------------------------------------------------------------------
# Feature: Monitor
# ---------------------------------------------------------------------------


def command_monitor(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    run = resolve_run(state, args.run_id)

    interactive = resolve_interactive(args)
    interval = args.interval
    if interactive and interval == 60:
        interval = wizard_int("Check interval (seconds)", default=60)

    output_mode = args.output
    status_file_path = args.status_file

    return monitor_loop(repo_root, run["run_id"], interval, output_mode, status_file_path)


def monitor_loop(
    repo_root: Path,
    run_id: str,
    interval: int,
    output_mode: str,
    status_file_path: str | None,
) -> int:
    """Blocking loop: reload state, print progress, sleep. Exits on run completion or Ctrl-C."""
    iteration = 0
    try:
        while True:
            iteration += 1
            state = load_state(repo_root)
            run = state.get("runs", {}).get(run_id)
            if run is None:
                print(f"Run {run_id} not found.")
                return 1

            update_text = format_monitor_update(run, iteration)
            if output_mode == "terminal":
                print(update_text)
            elif output_mode == "file" and status_file_path:
                write_monitor_status_file(Path(status_file_path), run)
                print(f"[{iteration}] status written to {status_file_path}")

            if run.get("status") in TERMINAL_RUN_STATUSES:
                print(f"Run {run_id} has {run['status']}.")
                return 0

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
        return 0


def format_monitor_update(run: dict[str, Any], iteration: int) -> str:
    """Format a single progress line."""
    rounds_done = run.get("rounds_completed", 0)
    rounds_target = run.get("execution", {}).get("rounds") or "-"
    best = run.get("best_metric")
    status = run.get("status", "unknown")
    early_exit = run.get("early_exit", {})
    stalled = early_exit.get("rounds_without_improvement", 0)
    patience = early_exit.get("patience")
    timestamp = now_iso()

    parts = [
        f"[{iteration}] {timestamp}",
        f"status={status}",
        f"rounds={rounds_done}/{rounds_target}",
        f"best={format_metric_value(best)}",
    ]
    if patience:
        parts.append(f"stalled={stalled}/{patience}")
    return "  ".join(parts)


def write_monitor_status_file(path: Path, run: dict[str, Any]) -> None:
    """Write a machine-readable status snapshot."""
    snapshot = {
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "rounds_completed": run.get("rounds_completed", 0),
        "rounds_target": run.get("execution", {}).get("rounds"),
        "best_metric": run.get("best_metric"),
        "best_candidate_id": run.get("best_candidate_id"),
        "early_exit": run.get("early_exit", {}),
        "timestamp": now_iso(),
    }
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Feature: Comparison runs (create / delete)
# ---------------------------------------------------------------------------
#
# A comparison run holds "arms". Each arm starts with a setup worktree where the
# structural change is made (implement an approach, or repair references after a
# deletion). `arm-ready` commits the setup and starts an ordinary optimize child
# run seeded from it, so every arm is tuned with the same budget. A tuned
# `control` arm (no structural change) is always included, so gains from tuning
# are not credited to the change itself; for delete runs it is the pre-deletion
# baseline.

MAX_CREATE_APPROACHES = 26


def command_create(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    state = ensure_scanned(repo_root)

    interactive = resolve_interactive(args)

    feature_description = args.feature
    if not feature_description and interactive:
        feature_description = wizard_input("Describe the feature to create")
    if not feature_description:
        raise SystemExit("--feature is required: describe the feature to create")

    part = resolve_part(state, args.part)
    if part is None and interactive:
        part_ids = [p["id"] for p in state.get("parts", [])]
        if part_ids:
            chosen = wizard_select("Which part does the feature relate to?", part_ids)
            part = resolve_part(state, chosen)
    if part is None:
        raise SystemExit("unable to resolve part; run scan first or pass --part")

    if not 1 <= args.candidates <= MAX_CREATE_APPROACHES:
        raise SystemExit(f"--candidates must be between 1 and {MAX_CREATE_APPROACHES}")
    config = comparison_config(args, part, interactive)

    approach_labels = [f"approach-{chr(65 + i)}" for i in range(args.candidates)]
    create_info = {
        "feature_description": feature_description,
        "num_approaches": args.candidates,
        "affected_parts": identify_affected_parts(state, [part["id"]]),
        "approach_labels": approach_labels,
    }
    arms = [("control", "control")] + [(label, "approach") for label in approach_labels]
    tune_scope = (
        parse_tune_scope(repo_root, args.tune_scope)
        if args.tune_scope
        else default_tune_scope(state, part, "create")
    )

    with state_lock(repo_root):
        state = load_state(repo_root)
        parent = create_comparison_run(
            repo_root, state, part, config, "create", arms, tune_scope, create_info=create_info
        )
        write_state(repo_root, state)

    emit(comparison_summary(parent), getattr(args, "json", False))
    return 0


def command_delete(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    state = ensure_scanned(repo_root)

    interactive = resolve_interactive(args)

    part = resolve_part(state, args.part)
    if part is None and interactive:
        part_ids = [p["id"] for p in state.get("parts", [])]
        if part_ids:
            chosen = wizard_select("Which part to delete?", part_ids)
            part = resolve_part(state, chosen)
    if part is None:
        raise SystemExit("unable to resolve part; run scan first or pass --part")

    dependents = find_delete_dependents(state, part["id"])

    if interactive:
        print(f"\nDeleting: `{part['id']}`")
        if dependents:
            print(f"Affected dependents: {', '.join(dependents)}")
        else:
            print("No dependents found.")
        if not wizard_confirm("Proceed with deletion run?"):
            print("Cancelled.")
            return 0

    config = comparison_config(args, part, interactive)
    delete_info = {
        "deleted_part_id": part["id"],
        "dependent_parts": dependents,
        "affected_parts": identify_affected_parts(state, [part["id"]]),
    }
    arms = [("control", "control"), ("deleted", "deletion")]
    tune_scope = (
        parse_tune_scope(repo_root, args.tune_scope)
        if args.tune_scope
        else default_tune_scope(state, part, "delete")
    )

    with state_lock(repo_root):
        state = load_state(repo_root)
        parent = create_comparison_run(
            repo_root, state, part, config, "delete", arms, tune_scope, delete_info=delete_info
        )
        write_state(repo_root, state)

    emit(comparison_summary(parent), getattr(args, "json", False))
    return 0


def comparison_config(args: argparse.Namespace, part: dict[str, Any], interactive: bool) -> dict[str, Any]:
    metric_name = args.metric
    metric_goal = args.metric_goal
    metric_command = args.metric_command
    if interactive:
        metric_name = prompt_if_missing(metric_name, "Metric name")
        metric_goal = prompt_if_missing(metric_goal, "Metric goal [minimize|maximize]")
        metric_command = prompt_if_missing(metric_command, "Metric command")
    if not metric_name or not metric_goal or not metric_command:
        raise SystemExit("metric, metric-goal, and metric-command are required for comparison runs")

    config = merge_config(
        part=part,
        existing={},
        metric_name=metric_name,
        metric_goal=metric_goal,
        metric_command=metric_command,
        metric_regex=DEFAULT_METRIC_REGEX,
        mode="sequential",
        rounds=args.rounds,
        stop_rule=validate_stop_rule(args.stop_rule),
        parallelism=1,
        entrypoint_type="part",
        entrypoint_path=part["id"],
        metric_preset=None,
        command_suggestion=None,
        metric_timeout=args.metric_timeout,
    )
    normalize_execution_defaults(config["execution"])
    missing = missing_run_fields(config)
    if missing:
        raise SystemExit("comparison run config is incomplete: " + ", ".join(missing))
    return config


def identify_affected_parts(state: dict[str, Any], target_part_ids: list[str]) -> list[str]:
    """Direct (1-hop) dependency neighbourhood of the targets, excluding the targets.

    Walking the graph transitively returns the whole connected component, which is
    far too broad to tune.
    """
    targets = set(target_part_ids)
    parts_by_id = {p["id"]: p for p in state.get("parts", [])}
    affected: set[str] = set()
    for target in targets:
        part = parts_by_id.get(target)
        if part:
            affected.update(part.get("dependencies", []))
            affected.update(part.get("dependents", []))
    return sorted(affected - targets)


def find_delete_dependents(state: dict[str, Any], part_id: str) -> list[str]:
    """Find all parts that depend on the given part, transitively."""
    dependents: set[str] = set()
    parts_by_id = {p["id"]: p for p in state.get("parts", [])}
    queue = [part_id]

    while queue:
        current = queue.pop(0)
        part = parts_by_id.get(current)
        if part:
            for dep in part.get("dependents", []):
                if dep not in dependents:
                    dependents.add(dep)
                    queue.append(dep)

    return sorted(dependents)


def apply_deletion_to_worktree(worktree_path: Path, part_id: str) -> None:
    """Remove the file identified by part_id from the worktree and commit."""
    target = worktree_path / part_id
    if target.exists():
        target.unlink()
        commit_worktree_changes(worktree_path, f"autoresearch: delete {part_id}")


def arm_child_run_id(parent_run_id: str, arm_id: str) -> str:
    return f"{parent_run_id}-{arm_id}"


# Tuning scope: the files an arm's tuning loop may change. Entries are repo-relative
# files, or directory prefixes ending in "/". Setup is never restricted.


def parse_tune_scope(repo_root: Path, raw: str) -> list[str]:
    entries: set[str] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        relative = normalize_repo_relative_path(repo_root, item.rstrip("/"))
        if relative in ("", "."):
            raise SystemExit("--tune-scope cannot be the whole repo; omit it or list files/directories")
        if item.endswith("/") or (repo_root / relative).is_dir():
            relative += "/"
        entries.add(relative)
    if not entries:
        raise SystemExit("--tune-scope is empty")
    return sorted(entries)


def default_tune_scope(state: dict[str, Any], part: dict[str, Any], run_type: str) -> list[str]:
    if run_type == "delete":
        # Only direct importers break when the part disappears.
        return sorted(part.get("dependents", []))
    return sorted({part["id"], *identify_affected_parts(state, [part["id"]])})


def path_in_scope(path: str, scope: list[str]) -> bool:
    return any(path == entry or (entry.endswith("/") and path.startswith(entry)) for entry in scope)


def changed_paths(worktree_path: Path, base_ref: str, commit: str) -> list[str]:
    output = git_stdout(worktree_path, ["diff", "--no-renames", "--name-only", base_ref, commit])
    return sorted(line for line in output.splitlines() if line.strip())


def out_of_scope_paths(run: dict[str, Any], worktree_path: Path, commit: str | None) -> list[str]:
    """Files changed since the run's base that fall outside its tuning scope (empty if unscoped)."""
    scope = run.get("tune_scope")
    if scope is None or not commit:
        return []
    return [path for path in changed_paths(worktree_path, run["base_ref"], commit) if not path_in_scope(path, scope)]


def scope_violation_message(candidate_id: str, paths: list[str], scope: list[str]) -> str:
    return (
        f"{candidate_id} changes files outside the arm's tuning scope: {', '.join(paths)}\n"
        f"tuning scope: {', '.join(scope) or '(empty)'}\n"
        "revert those edits and re-run evaluate, or pass --allow-out-of-scope to accept and flag it"
    )


def create_comparison_run(
    repo_root: Path,
    state: dict[str, Any],
    part: dict[str, Any],
    config: dict[str, Any],
    run_type: str,
    arms: list[tuple[str, str]],
    tune_scope: list[str],
    create_info: dict[str, Any] | None = None,
    delete_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warn_if_checkout_dirty(repo_root)
    run_id = build_run_id(part["id"], state, repo_root)
    run_dir = runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    worktree_root = default_worktree_root(repo_root) / run_id
    worktree_root.mkdir(parents=True, exist_ok=True)
    base_ref = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()

    parent = {
        "run_id": run_id,
        "part_id": part["id"],
        "run_type": run_type,
        "status": "running",
        "created_at": now_iso(),
        "run_dir": str(run_dir),
        "program_path": str(run_dir / "program.md"),
        "results_path": str(run_dir / "results.tsv"),
        "worktree_root": str(worktree_root),
        "base_ref": base_ref,
        "current_base_branch": None,
        "best_candidate_id": None,
        "best_metric": None,
        "execution": config["execution"],
        "metric": config["metric"],
        "rounds_completed": 0,
        "candidates": [],
        "early_exit": {
            "patience": None, "threshold": None,
            "rounds_without_improvement": 0, "triggered": False, "trigger_reason": None,
        },
        "create_info": create_info,
        "delete_info": delete_info,
        "arms": [],
        "compare": None,
        "tune_scope": tune_scope,
    }
    Path(parent["results_path"]).write_text(RESULTS_HEADER)

    for arm_id, kind in arms:
        child_run_id = arm_child_run_id(run_id, arm_id)
        arm_root = worktree_root / arm_id
        setup = create_candidate_worktree(
            repo_root=repo_root,
            worktree_path=arm_root / "seed",
            branch_name=f"autoresearch/{slugify(part['id'])}/{child_run_id}/seed",
            base_ref=base_ref,
            candidate_id="seed",
            based_on=base_ref,
        )
        parent["arms"].append(
            {
                "arm_id": arm_id,
                "kind": kind,
                "phase": "setup",
                "worktree_root": str(arm_root),
                "setup": setup,
                "setup_commit": None,
                "child_run_id": None,
                "ready_at": None,
            }
        )

    state.setdefault("runs", {})[run_id] = parent
    state.setdefault("selection", {})["part_id"] = part["id"]
    state.setdefault("selection", {})["active_run_id"] = run_id

    if run_type == "delete":
        deleted_arm = get_arm(parent, "deleted")
        apply_deletion_to_worktree(Path(deleted_arm["setup"]["worktree_path"]), part["id"])

    # The control arm has no setup work, so it can start tuning immediately.
    ready_arm(repo_root, state, parent, get_arm(parent, "control"))

    Path(parent["program_path"]).write_text(render_comparison_program(repo_root, parent))
    return parent


def get_arm(parent: dict[str, Any], arm_id: str) -> dict[str, Any]:
    for arm in parent.get("arms", []):
        if arm["arm_id"] == arm_id:
            return arm
    known = ", ".join(arm["arm_id"] for arm in parent.get("arms", []))
    raise SystemExit(f"unknown arm {arm_id!r} for run {parent['run_id']}; arms: {known}")


def resolve_comparison_run(state: dict[str, Any], run_id: str | None) -> dict[str, Any]:
    run = resolve_run(state, run_id)
    if run.get("parent_run_id"):
        run = resolve_run(state, run["parent_run_id"])
    if "arms" not in run:
        if run.get("run_type") in ("create", "delete"):
            raise SystemExit(
                f"run {run['run_id']} is a legacy {run['run_type']} run without arms; "
                "recreate it to get tuned, comparable arms"
            )
        raise SystemExit(f"run {run['run_id']} is not a create/delete comparison run")
    return run


def resolve_target_run(state: dict[str, Any], run_id: str | None, arm_id: str | None) -> dict[str, Any]:
    """Resolve the run a loop command acts on; `--arm` maps a comparison run to that arm's tuning run."""
    run = resolve_run(state, run_id)
    if arm_id:
        parent = resolve_comparison_run(state, run["run_id"])
        arm = get_arm(parent, arm_id)
        if not arm.get("child_run_id"):
            raise SystemExit(
                f"arm {arm_id} is still in setup; make the change in {arm['setup']['worktree_path']} "
                f"then run: arm-ready --run-id {parent['run_id']} --arm {arm_id}"
            )
        return resolve_run(state, arm["child_run_id"])
    if "arms" in run:
        arms = "|".join(arm["arm_id"] for arm in run["arms"])
        raise SystemExit(f"run {run['run_id']} is a comparison run; pass --arm <{arms}>")
    return run


def ready_arm(
    repo_root: Path, state: dict[str, Any], parent: dict[str, Any], arm: dict[str, Any]
) -> dict[str, Any]:
    """Commit the arm's setup and start its optimize child run from that commit."""
    if arm.get("child_run_id"):
        raise SystemExit(f"arm {arm['arm_id']} is already tuning in run {arm['child_run_id']}")
    setup = arm["setup"]
    setup_path = Path(setup["worktree_path"])
    if not setup_path.exists():
        raise SystemExit(f"setup worktree is missing: {setup_path}")
    part = resolve_part(state, parent["part_id"])
    if part is None:
        raise SystemExit(f"part {parent['part_id']} is no longer in the scan; rescan before readying arms")

    setup_commit = commit_worktree_changes(
        setup_path, f"autoresearch: {parent['run_id']} {arm['arm_id']} setup"
    )
    config = {
        "metric": copy.deepcopy(parent["metric"]),
        "execution": copy.deepcopy(parent["execution"]),
    }
    child = init_optimize_run(
        repo_root,
        part,
        config,
        run_id=arm_child_run_id(parent["run_id"], arm["arm_id"]),
        worktree_root=Path(arm["worktree_root"]),
        seed=copy.deepcopy(setup),
        base_ref=setup_commit,
    )
    child["parent_run_id"] = parent["run_id"]
    child["arm_id"] = arm["arm_id"]
    if parent.get("tune_scope") is not None:
        # Files the setup touched (new feature modules, repaired importers) are tunable too.
        setup_changes = changed_paths(setup_path, parent["base_ref"], setup_commit)
        child["tune_scope"] = sorted(set(parent["tune_scope"]) | set(setup_changes))
        with Path(child["program_path"]).open("a") as handle:
            handle.write(render_scope_section(child["tune_scope"]))
    state.setdefault("runs", {})[child["run_id"]] = child
    arm.update(
        {
            "phase": "tuning",
            "setup_commit": setup_commit,
            "child_run_id": child["run_id"],
            "ready_at": now_iso(),
        }
    )
    return child


def render_scope_section(scope: list[str]) -> str:
    lines = [
        "",
        "## Tuning scope (enforced)",
        "",
        "`evaluate` and `record` reject candidates that change files outside this list",
        "(directories end in `/`). Use `--allow-out-of-scope` only for a deliberate exception;",
        "such candidates are flagged in `compare`.",
        "",
    ]
    lines.extend(f"- `{entry}`" for entry in scope)
    if not scope:
        lines.append("- (empty: no file may change)")
    return "\n".join(lines) + "\n"


def command_arm_ready(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    with state_lock(repo_root):
        state = load_state(repo_root)
        parent = resolve_comparison_run(state, args.run_id)
        arm = get_arm(parent, args.arm)
        child = ready_arm(repo_root, state, parent, arm)
        write_state(repo_root, state)
    emit(
        {
            "run_id": parent["run_id"],
            "arm": arm["arm_id"],
            "child_run_id": child["run_id"],
            "setup_commit": arm["setup_commit"],
            "program_path": child["program_path"],
            "next": f"evaluate and record `seed` with --arm {arm['arm_id']} to measure the setup score",
        },
        args.json,
    )
    return 0


def refresh_comparison_status(state: dict[str, Any], parent: dict[str, Any]) -> None:
    """Sync arm phases from their child runs; the parent completes when every arm has."""
    all_done = True
    for arm in parent.get("arms", []):
        child = state.get("runs", {}).get(arm.get("child_run_id") or "")
        if child and child.get("status") in TERMINAL_RUN_STATUSES:
            arm["phase"] = "done"
        elif arm.get("phase") != "abandoned":
            all_done = False
    if all_done and parent.get("status") not in TERMINAL_RUN_STATUSES:
        parent["status"] = "completed"
        parent["stop_reason"] = "all arms finished tuning"


def compare_arms(state: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    refresh_comparison_status(state, parent)
    goal = parent["metric"].get("goal")
    rows: list[dict[str, Any]] = []
    for arm in parent["arms"]:
        child = state.get("runs", {}).get(arm.get("child_run_id") or "")
        seed = get_candidate(child, "seed") if child else None
        setup_metric = (seed or {}).get("result", {}).get("metric_value")
        best_metric = child.get("best_metric") if child else None
        rows.append(
            {
                "arm_id": arm["arm_id"],
                "kind": arm["kind"],
                "phase": arm["phase"],
                "child_run_id": arm.get("child_run_id"),
                "setup_metric": setup_metric,
                "best_metric": best_metric,
                "best_candidate_id": child.get("best_candidate_id") if child else None,
                "rounds_completed": child.get("rounds_completed", 0) if child else 0,
                "stop_reason": child.get("stop_reason") if child else None,
                "out_of_scope_candidates": [
                    candidate["candidate_id"]
                    for candidate in (child or {}).get("candidates", [])
                    if candidate.get("result", {}).get("out_of_scope")
                ],
                "tuning_gain": (
                    best_metric - setup_metric
                    if best_metric is not None and setup_metric is not None
                    else None
                ),
            }
        )

    control_best = next(row["best_metric"] for row in rows if row["arm_id"] == "control")
    for row in rows:
        row["delta_vs_control"] = (
            row["best_metric"] - control_best
            if row["best_metric"] is not None and control_best is not None
            else None
        )

    # Ties go to the earlier arm, so the control (status quo) wins a tie.
    winner = None
    for row in rows:
        if row["best_metric"] is None:
            continue
        if winner is None or is_better_metric(row["best_metric"], winner["best_metric"], goal):
            winner = row

    return {
        "compared_at": now_iso(),
        "metric_name": parent["metric"].get("name"),
        "goal": goal,
        "arms": rows,
        "winner_arm": winner["arm_id"] if winner else None,
        "incomplete_arms": [row["arm_id"] for row in rows if row["phase"] != "done"],
    }


def format_compare_table(result: dict[str, Any]) -> str:
    lines = [
        f"Metric: `{result['metric_name']}` ({result['goal']})",
        "",
        "| arm | phase | setup | tuned best | tuning gain | vs control | rounds |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in result["arms"]:
        lines.append(
            "| {arm} | {phase} | {setup} | {best} | {gain} | {delta} | {rounds} |".format(
                arm=row["arm_id"] + (" *" if row["arm_id"] == result["winner_arm"] else ""),
                phase=row["phase"],
                setup=format_metric_value(row["setup_metric"]),
                best=format_metric_value(row["best_metric"]),
                gain=format_metric_delta(row["tuning_gain"]),
                delta=format_metric_delta(row["delta_vs_control"]),
                rounds=row["rounds_completed"],
            )
        )
    lines.append("")
    if result["winner_arm"]:
        lines.append(f"Winner (*): `{result['winner_arm']}`")
    else:
        lines.append("Winner: none yet (no arm has a recorded metric)")
    if result["incomplete_arms"]:
        lines.append(
            "Incomplete arms (comparison is provisional): " + ", ".join(result["incomplete_arms"])
        )
    flagged = [
        f"{row['arm_id']}/{candidate_id}"
        for row in result["arms"]
        for candidate_id in row.get("out_of_scope_candidates", [])
    ]
    if flagged:
        lines.append("Out-of-scope edits accepted (comparison may be unfair): " + ", ".join(flagged))
    return "\n".join(lines)


def command_compare(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    with state_lock(repo_root):
        state = load_state(repo_root)
        parent = resolve_comparison_run(state, args.run_id)
        result = compare_arms(state, parent)
        parent["compare"] = result
        write_state(repo_root, state)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_compare_table(result))
    return 0


def finalize_comparison(
    repo_root: Path, state: dict[str, Any], parent: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    refresh_comparison_status(state, parent)
    unfinished = [arm for arm in parent["arms"] if arm["phase"] not in ("done", "abandoned")]
    if unfinished and not args.stop:
        names = ", ".join(arm["arm_id"] for arm in unfinished)
        raise SystemExit(f"arms still in progress: {names}; pass --stop to end them and finalize")
    for arm in unfinished:
        child = state.get("runs", {}).get(arm.get("child_run_id") or "")
        if child:
            child["status"] = "completed"
            child["stop_reason"] = "stopped by finalize"
            arm["phase"] = "done"
        else:
            arm["phase"] = "abandoned"
    refresh_comparison_status(state, parent)
    if parent.get("status") not in TERMINAL_RUN_STATUSES:
        parent["status"] = "completed"
        parent["stop_reason"] = "stopped by finalize"

    result = compare_arms(state, parent)
    parent["compare"] = result
    winner_arm_id = args.arm or result["winner_arm"]

    winner_branch = None
    winner_candidate_id = None
    if winner_arm_id:
        winner_child = state.get("runs", {}).get(get_arm(parent, winner_arm_id).get("child_run_id") or "")
        if winner_child is None:
            raise SystemExit(f"arm {winner_arm_id} never started tuning; nothing to merge from it")
        winner_candidate_id = winner_child.get("best_candidate_id") or "seed"
        winner_branch = get_candidate(winner_child, winner_candidate_id)["branch"]
    has_changes = bool(winner_branch) and branch_differs_from(repo_root, winner_branch, parent["base_ref"])

    # Merge first: if it fails, nothing has been removed yet.
    merged = False
    if args.merge and has_changes:
        squash_merge_into_checkout(repo_root, winner_branch)
        merged = True

    removed: list[str] = []
    skipped: list[dict[str, str]] = []
    pruned: list[str] = []
    for arm in parent["arms"]:
        child = state.get("runs", {}).get(arm.get("child_run_id") or "")
        run_like = child or {"candidates": [arm["setup"]], "worktree_root": arm["worktree_root"]}
        keep = winner_candidate_id if arm["arm_id"] == winner_arm_id and args.keep_best_worktree else None
        arm_removed, arm_skipped = remove_run_worktrees(repo_root, run_like, keep, args.force)
        removed.extend(f"{arm['arm_id']}/{item}" for item in arm_removed)
        skipped.extend({**item, "item": f"{arm['arm_id']}/{item['item']}"} for item in arm_skipped)
        if args.prune_branches:
            arm_pruned, branch_skips = prune_run_branches(repo_root, run_like, keep_branch=winner_branch)
            pruned.extend(arm_pruned)
            skipped.extend(branch_skips)
        if child:
            refresh_single_run_worktrees(child)
    try:
        Path(parent["worktree_root"]).rmdir()
    except OSError:
        pass

    parent["finalized"] = {
        "finalized_at": now_iso(),
        "winner_arm": winner_arm_id,
        "best_candidate_id": winner_candidate_id,
        "best_branch": winner_branch,
        "best_has_changes": has_changes,
        "merged": merged,
        "removed_worktrees": removed,
        "pruned_branches": pruned,
        "skipped": skipped,
    }
    return {
        "run_id": parent["run_id"],
        "status": parent["status"],
        "compare": result,
        **parent["finalized"],
        "next_steps": finalize_next_steps(parent["base_ref"], winner_branch, has_changes, merged, skipped),
    }


def comparison_summary(parent: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": parent["run_id"],
        "run_type": parent["run_type"],
        "part_id": parent["part_id"],
        "arms": [
            {
                "arm": arm["arm_id"],
                "kind": arm["kind"],
                "phase": arm["phase"],
                "setup_worktree": arm["setup"]["worktree_path"],
                "child_run_id": arm.get("child_run_id"),
            }
            for arm in parent["arms"]
        ],
        "affected_parts": (parent.get("create_info") or parent.get("delete_info") or {}).get("affected_parts", []),
        "tune_scope": parent.get("tune_scope"),
        "program_path": parent["program_path"],
    }


def render_comparison_program(repo_root: Path, parent: dict[str, Any]) -> str:
    script = f"python3 {helper_script_path()}"
    run_id = parent["run_id"]
    metric = parent["metric"]
    execution = parent["execution"]
    is_create = parent["run_type"] == "create"
    info = parent.get("create_info") or parent.get("delete_info") or {}

    lines = [f"# {'Create' if is_create else 'Delete'} Comparison Run: {run_id}", ""]
    if is_create:
        lines.append(f"Feature: {info['feature_description']}")
    else:
        lines.append(f"Deleted part: `{info['deleted_part_id']}`")
    lines.extend(
        [
            f"Target part: `{parent['part_id']}`",
            "",
            "Every arm is tuned with the same budget and compared against a tuned `control` arm",
            "(no structural change), so gains from tuning are not credited to the change itself.",
            "",
            "## Locked config (every arm)",
            "",
            f"- Metric: `{metric['name']}` ({metric['goal']})",
            f"- Metric command: `{metric['command']}`",
            f"- Rounds per arm: `{execution.get('rounds')}`",
            f"- Stop rule per arm: `{execution.get('stop_rule') or 'none'}`",
            "",
            "## Tuning scope (enforced)",
            "",
            "During tuning, `evaluate` and `record` reject candidates that change files outside this",
            "list; each arm also may change the files its own setup changed. Setup itself is unrestricted.",
            "",
        ]
    )
    scope = parent.get("tune_scope") or []
    lines.extend(f"- `{item}`" for item in scope)
    if not scope:
        lines.append("- (empty: only files changed during setup)")
    lines.extend(["", "## Arms", ""])
    for arm in parent["arms"]:
        child_program = runs_dir(repo_root) / arm_child_run_id(run_id, arm["arm_id"]) / "program.md"
        lines.append(
            f"- `{arm['arm_id']}` ({arm['kind']}): setup worktree `{arm['setup']['worktree_path']}`, "
            f"tuning program `{child_program}`"
        )

    lines.extend(["", "## Phase 1: setup", ""])
    if is_create:
        lines.extend(
            [
                "Implement the feature differently in each `approach-*` setup worktree. Leave `control` untouched;",
                "it is already tuning-ready. When an approach is implemented:",
            ]
        )
    else:
        lines.extend(
            [
                f"The `deleted` setup worktree already has `{info['deleted_part_id']}` removed and committed.",
                "Fix broken imports and references there. `control` keeps the part and is already tuning-ready.",
                "When the deletion compiles and runs:",
            ]
        )
    lines.extend(["", "```bash", f"{script} arm-ready --run-id {run_id} --arm <arm>", "```", ""])

    lines.extend(
        [
            "## Phase 2: tune every arm with the same budget",
            "",
            "Each ready arm has its own optimize run (see its tuning program). Measure the setup score first,",
            "then run the usual loop, editing only files in the tuning scope:",
            "",
            "```bash",
            f"{script} evaluate --run-id {run_id} --arm <arm> --candidate seed",
            f"{script} record --run-id {run_id} --arm <arm> --candidate seed --status auto --description \"setup\"",
            f"{script} allocate --run-id {run_id} --arm <arm>",
            f"{script} evaluate --run-id {run_id} --arm <arm> --candidate candidate-XYZ",
            f"{script} record --run-id {run_id} --arm <arm> --candidate candidate-XYZ --status auto --description \"...\"",
            "```",
            "",
            "An arm is done when its rounds target or stop rule is met.",
            "",
            "## Phase 3: compare",
            "",
            "```bash",
            f"{script} compare --run-id {run_id}",
            "```",
            "",
            "## Phase 4: merge the winner and clean up",
            "",
            "```bash",
            f"{script} finalize --run-id {run_id} --merge",
            "```",
            "",
            "If `control` wins, no approach beat the status quo once both were tuned; merging it applies",
            "only the tuning changes.",
            "",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Feature: Finalize (merge-back + cleanup)
# ---------------------------------------------------------------------------


def command_finalize(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    with state_lock(repo_root):
        state = load_state(repo_root)
        run = resolve_run(state, args.run_id)
        if run.get("parent_run_id"):
            raise SystemExit(
                f"run {run['run_id']} is arm {run.get('arm_id')} of comparison run "
                f"{run['parent_run_id']}; finalize that run instead"
            )
        if "arms" in run:
            payload = finalize_comparison(repo_root, state, run, args)
        else:
            if args.arm:
                raise SystemExit("--arm only applies to create/delete comparison runs")
            payload = finalize_run(repo_root, run, args)
        write_state(repo_root, state)
    emit(payload, args.json)
    return 0


def finalize_next_steps(
    base_ref: str, branch: str | None, has_changes: bool, merged: bool, skipped: list[dict[str, str]]
) -> list[str]:
    if not has_changes:
        steps = ["no candidate changed the base commit; nothing to merge"]
    elif merged:
        steps = [
            f"review the staged squash of {branch}: git diff --cached",
            "commit it when satisfied, or discard with: git reset --merge",
        ]
    else:
        steps = [
            f"inspect: git diff {base_ref[:12]} {branch}",
            f"merge:   git merge --squash {branch}  (or rerun finalize with --merge)",
        ]
    if skipped:
        steps.append("some items were skipped; rerun with --force to remove dirty worktrees")
    return steps


def finalize_run(repo_root: Path, run: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if run.get("status") not in TERMINAL_RUN_STATUSES:
        if not args.stop:
            raise SystemExit(
                f"run {run['run_id']} is still {run.get('status')}; pass --stop to end it and finalize"
            )
        run["status"] = "completed"
        run["stop_reason"] = "stopped by finalize"

    best = get_candidate(run, run["best_candidate_id"]) if run.get("best_candidate_id") else None
    best_branch = best["branch"] if best else None
    best_has_changes = bool(best_branch) and branch_differs_from(repo_root, best_branch, run["base_ref"])

    # Merge first: if it fails, nothing has been removed yet.
    merged = False
    if args.merge and best_has_changes:
        squash_merge_into_checkout(repo_root, best_branch)
        merged = True

    removed, skipped = remove_run_worktrees(
        repo_root,
        run,
        keep_candidate_id=best["candidate_id"] if best and args.keep_best_worktree else None,
        force=args.force,
    )
    pruned_branches: list[str] = []
    if args.prune_branches:
        pruned_branches, branch_skips = prune_run_branches(repo_root, run, keep_branch=best_branch)
        skipped.extend(branch_skips)

    refresh_single_run_worktrees(run)

    run["finalized"] = {
        "finalized_at": now_iso(),
        "best_candidate_id": best["candidate_id"] if best else None,
        "best_branch": best_branch,
        "best_metric": run.get("best_metric"),
        "best_has_changes": best_has_changes,
        "merged": merged,
        "removed_worktrees": removed,
        "pruned_branches": pruned_branches,
        "skipped": skipped,
    }

    return {
        "run_id": run["run_id"],
        "status": run["status"],
        **run["finalized"],
        "next_steps": finalize_next_steps(run["base_ref"], best_branch, best_has_changes, merged, skipped),
    }


def branch_differs_from(repo_root: Path, branch: str, base_ref: str) -> bool:
    completed = git_run(repo_root, ["rev-parse", "--verify", f"{branch}^{{commit}}"])
    if completed.returncode != 0:
        return False
    return completed.stdout.strip() != base_ref


def squash_merge_into_checkout(repo_root: Path, branch: str) -> None:
    dirty = git_stdout(repo_root, ["status", "--porcelain", "--untracked-files=no"]).strip()
    if dirty:
        raise SystemExit(
            "the main checkout has uncommitted changes to tracked files; commit or stash them before --merge"
        )
    merge = git_run(repo_root, ["merge", "--squash", branch])
    if merge.returncode != 0:
        git_run(repo_root, ["reset", "--merge"])
        detail = (merge.stdout + merge.stderr).strip()
        raise SystemExit(
            f"squash merge of {branch} failed and was rolled back; nothing was cleaned up.\n{detail}\n"
            f"Resolve manually with: git merge --squash {branch}"
        )


def remove_run_worktrees(
    repo_root: Path,
    run: dict[str, Any],
    keep_candidate_id: str | None,
    force: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    removed: list[str] = []
    skipped: list[dict[str, str]] = []
    for candidate in run.get("candidates", []):
        path = Path(candidate["worktree_path"])
        if candidate["candidate_id"] == keep_candidate_id or not path.exists():
            continue
        command = ["worktree", "remove", *(["--force"] if force else []), str(path)]
        completed = git_run(repo_root, command)
        if completed.returncode == 0:
            removed.append(candidate["candidate_id"])
        else:
            skipped.append(
                {
                    "item": candidate["candidate_id"],
                    "reason": (completed.stderr or completed.stdout).strip() or "git worktree remove failed",
                }
            )
    git_run(repo_root, ["worktree", "prune"])
    worktree_root = Path(run["worktree_root"])
    try:
        worktree_root.rmdir()
    except OSError:
        pass  # not empty (kept/skipped worktrees) or already gone
    return removed, skipped


def prune_run_branches(
    repo_root: Path, run: dict[str, Any], keep_branch: str | None
) -> tuple[list[str], list[dict[str, str]]]:
    pruned: list[str] = []
    skipped: list[dict[str, str]] = []
    for candidate in run.get("candidates", []):
        branch = candidate["branch"]
        if branch == keep_branch:
            continue
        exists = git_run(repo_root, ["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
        if exists.returncode != 0:
            continue
        completed = git_run(repo_root, ["branch", "-D", branch])
        if completed.returncode == 0:
            pruned.append(branch)
        else:
            skipped.append(
                {"item": branch, "reason": (completed.stderr or completed.stdout).strip() or "branch -D failed"}
            )
    return pruned, skipped
