from __future__ import annotations

import argparse
import ast
import csv
import datetime as dt
import json
import os
import re
import resource
import shlex
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath
from string import Template
from typing import Any

STATE_DIRNAME = ".autoresearch-wrapper"
STATE_FILENAME = "state.json"
STATUS_FILENAME = "STATUS.md"
RUNS_DIRNAME = "runs"
PLANS_DIRNAME = "plans"
REFERENCE_DIRNAME = "reference"
REFERENCE_REPO_URL = "https://github.com/karpathy/autoresearch.git"
REFERENCE_REPO_NAME = "autoresearch-upstream"
DEFAULT_METRIC_REGEX = r"METRIC\s*=\s*(?P<value>[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
PLAN_METADATA_FILENAME = "metadata.json"
PLAN_DEPENDENCIES_FILENAME = "dependencies.md"
PLAN_NOTES_FILENAME = "notes.md"
WRAP_DEFAULT_ROUNDS = 3
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
    "scan",
    "wrap",
    "configure",
    "status",
    "run",
    "allocate",
    "evaluate",
    "record",
    "reference",
    "preset-metric",
    "flow",
    "resources",
    "monitor",
    "create",
    "delete",
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


def main(argv: list[str] | None = None) -> int:
    argv = normalize_entry_argv(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dependency-aware autoresearch wrapper helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Analyze the repo and persist part status.")
    add_repo_arg(scan)
    scan.add_argument(
        "--full-summary",
        action="store_true",
        help="Print the full language/directory listing and full dependency graph.",
    )
    add_interactive_arg(scan)
    scan.set_defaults(func=command_scan)

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
    wrap.add_argument("--stop-rule", help="Optional textual stop rule.")
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
    configure.add_argument("--stop-rule", help="Optional textual stop rule.")
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
    allocate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    allocate.set_defaults(func=command_allocate)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a candidate or seed worktree.")
    add_repo_arg(evaluate)
    evaluate.add_argument("--run-id", help="Run id. Defaults to the active run.")
    evaluate.add_argument("--candidate", required=True, help="Candidate id.")
    evaluate.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    evaluate.set_defaults(func=command_evaluate)

    record = subparsers.add_parser("record", help="Persist the result of a candidate evaluation.")
    add_repo_arg(record)
    record.add_argument("--run-id", help="Run id. Defaults to the active run.")
    record.add_argument("--candidate", required=True, help="Candidate id.")
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
    flow.add_argument(
        "--width",
        type=int,
        default=28,
        help="Plot width for the ASCII metric chart.",
    )
    flow.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    flow.set_defaults(func=command_flow)

    reference = subparsers.add_parser("reference", help="Clone or refresh the upstream reference.")
    add_repo_arg(reference)
    reference.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch updates if the reference repo already exists.",
    )
    reference.set_defaults(func=command_reference)

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

    resources = subparsers.add_parser("resources", help="Detect system resources and set concurrency defaults.")
    add_repo_arg(resources)
    resources.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(resources)
    resources.set_defaults(func=command_resources)

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
        help="Propose and compare candidate implementations for a new feature.",
    )
    add_repo_arg(create)
    create.add_argument("--part", help="Part id that the new feature relates to.")
    create.add_argument("--feature", help="Description of the feature to create.")
    create.add_argument(
        "--candidates", type=int, default=3, help="Number of candidate approaches."
    )
    create.add_argument("--metric-command", help="Metric command to evaluate each approach.")
    create.add_argument("--metric", help="Metric name.")
    create.add_argument(
        "--metric-goal",
        choices=("minimize", "maximize"),
        help="Metric direction.",
    )
    create.add_argument("--rounds", type=int, default=3, help="Optimization rounds per candidate.")
    create.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(create)
    create.set_defaults(func=command_create)

    delete = subparsers.add_parser(
        "delete",
        help="Delete a module and optimize dependent parameters.",
    )
    add_repo_arg(delete)
    delete.add_argument("--part", help="Part id to delete.")
    delete.add_argument("--metric-command", help="Metric command to evaluate post-deletion quality.")
    delete.add_argument("--metric", help="Metric name.")
    delete.add_argument(
        "--metric-goal",
        choices=("minimize", "maximize"),
        help="Metric direction.",
    )
    delete.add_argument("--rounds", type=int, default=3, help="Optimization rounds after deletion.")
    delete.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    add_interactive_arg(delete)
    delete.set_defaults(func=command_delete)

    return parser


def add_repo_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repo root or any path inside the repo.")


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
        return argv
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

    if args.full_summary:
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
    else:
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

    interactive = resolve_interactive(args)
    if not interactive or len(parts) < 2:
        return 0

    # Interactive: let user filter by group
    group_options: list[str] = []
    group_map: dict[str, list[dict[str, Any]]] = {}
    default_group = "all files"
    if len(focus_parts) < len(parts):
        default_group = f"core functionality ({len(focus_parts)} files)"
        group_options.append(default_group)
        group_map[default_group] = focus_parts
    group_options.append("all files")
    group_map["all files"] = parts
    for lang, lang_parts in lang_groups.items():
        label = f"{lang} ({len(lang_parts)} files)"
        group_options.append(label)
        group_map[label] = lang_parts
    for directory, dir_parts in dir_groups.items():
        label = f"{directory}/ ({len(dir_parts)} files)"
        if label not in group_options:
            group_options.append(label)
            group_map[label] = dir_parts

    chosen_group = wizard_select(
        "Which kind of files do you want to optimize?",
        group_options,
        default=default_group,
    )
    filtered_parts = group_map[chosen_group]

    if chosen_group != "all files":
        print(f"\n{len(filtered_parts)} files in scope.")
        print(f"\n{render_dependency_tree(filtered_parts)}\n")

    # Select a specific part
    part_ids = [p["id"] for p in filtered_parts]
    chosen = wizard_select("Select a part to optimize", part_ids)
    state.setdefault("selection", {})["part_id"] = chosen
    write_state(repo_root, state)
    print(f"selected: {chosen}")
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
        stop_rule=args.stop_rule or existing.get("execution", {}).get("stop_rule"),
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
    stop_rule = args.stop_rule or execution.get("stop_rule")
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
        stop_rule = stop_rule or input("Stop rule (optional): ").strip()
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


def command_run(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    state = ensure_scanned(repo_root)
    part = resolve_part(state, args.part or state.get("selection", {}).get("part_id"))
    if part is None:
        raise SystemExit("no selected part; configure one with the wrapper first")
    config = state.get("part_configs", {}).get(part["id"])
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
        run = create_run(repo_root, state, part, config)
    else:
        run["status"] = "running"
        run["resumed_at"] = now_iso()
        refresh_single_run_worktrees(run)

    state.setdefault("selection", {})["part_id"] = part["id"]
    state.setdefault("selection", {})["active_run_id"] = run["run_id"]
    write_state(repo_root, state)

    payload = {
        "run_id": run["run_id"],
        "part_id": part["id"],
        "program_path": run["program_path"],
        "active_candidates": [candidate["candidate_id"] for candidate in run["candidates"]],
    }
    emit(payload, args.json)
    return 0


def command_allocate(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    ensure_git_repo(repo_root)
    state = ensure_scanned(repo_root)
    run = resolve_run(state, args.run_id)
    candidate = allocate_candidate(repo_root, run)
    write_state(repo_root, state)
    emit(candidate, args.json)
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    run = resolve_run(state, args.run_id)
    candidate = get_candidate(run, args.candidate)
    if candidate is None:
        raise SystemExit(f"unknown candidate: {args.candidate}")

    config = state["part_configs"][run["part_id"]]
    metric = config["metric"]
    worktree_path = Path(candidate["worktree_path"])
    if not worktree_path.exists():
        raise SystemExit(f"candidate worktree is missing: {worktree_path}")

    result = run_metric_command(
        metric_command=metric["command"],
        metric_regex=metric["regex"],
        cwd=worktree_path,
        log_dir=Path(run["run_dir"]) / "logs",
        candidate_id=candidate["candidate_id"],
    )
    candidate["latest_evaluation"] = result
    candidate["lifecycle"] = "evaluated" if result["exit_code"] == 0 else "failed"
    write_state(repo_root, state)
    emit(result, args.json)
    return 0


def command_record(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    run = resolve_run(state, args.run_id)
    candidate = get_candidate(run, args.candidate)
    if candidate is None:
        raise SystemExit(f"unknown candidate: {args.candidate}")

    config = state["part_configs"][run["part_id"]]
    metric_name = config["metric"]["name"]
    goal = config["metric"]["goal"]
    evaluation = candidate.get("latest_evaluation", {})
    metric_value = args.metric_value if args.metric_value is not None else evaluation.get("metric_value")
    if metric_value is None and args.status != "crash":
        raise SystemExit("no metric value available; run evaluate first or pass --metric-value")

    chosen_status = args.status
    if chosen_status == "auto":
        chosen_status = decide_status(run, goal, metric_value)

    candidate["result"] = {
        "status": chosen_status,
        "description": args.description,
        "metric_value": metric_value,
        "recorded_at": now_iso(),
    }
    candidate["lifecycle"] = chosen_status
    candidate["recorded"] = True

    previous_best_metric = run.get("best_metric")

    if chosen_status == "keep" and metric_value is not None:
        run["best_metric"] = metric_value
        run["best_candidate_id"] = candidate["candidate_id"]
        run["current_base_branch"] = candidate["branch"]

    if candidate["candidate_id"] != "seed":
        run["rounds_completed"] = count_completed_rounds(run)

    rounds_target = run["execution"].get("rounds")
    if rounds_target and run["rounds_completed"] >= rounds_target:
        run["status"] = "completed"
    else:
        run["status"] = "running"

    # Early exit check
    early_exit = run.get("early_exit", {})
    if early_exit.get("patience") and run["status"] == "running":
        update_early_exit_state(run, metric_value, previous_best_metric)
        exit_check = check_early_exit(run)
        if exit_check["should_exit"]:
            run["status"] = "early_exit"
            run["early_exit"]["triggered"] = True
            run["early_exit"]["trigger_reason"] = exit_check["reason"]

    append_result_row(run, candidate, metric_name, goal)
    write_state(repo_root, state)
    emit(candidate["result"], args.json)
    return 0


def command_reference(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    reference_dir = state_dir(repo_root) / REFERENCE_DIRNAME / REFERENCE_REPO_NAME
    reference_dir.parent.mkdir(parents=True, exist_ok=True)

    if reference_dir.exists():
        if args.refresh:
            git_run(reference_dir, ["fetch", "--all", "--prune"], check=True)
            action = "refreshed"
        else:
            action = "present"
    else:
        git_run(repo_root, ["clone", REFERENCE_REPO_URL, str(reference_dir)], check=True)
        action = "cloned"

    state = ensure_scanned(repo_root)
    state["reference"] = {
        "url": REFERENCE_REPO_URL,
        "path": str(reference_dir),
        "updated_at": now_iso(),
    }
    write_state(repo_root, state)
    print(f"{action} reference at {reference_dir}")
    return 0


def command_flow(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    state = ensure_scanned(repo_root)
    run = resolve_run(state, args.run_id)
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
    state["parts"] = parts
    state["dependency_graph"] = dependency_graph
    state["planning_workspace"] = {
        "root": str(plans_dir(repo_root)),
        "generated_at": now_iso(),
    }
    refresh_part_readiness(state)
    write_planning_workspace(repo_root, state)
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
        state.setdefault("resources", {
            "detected_at": None,
            "cpus": None,
            "memory_gb": None,
            "gpus": [],
            "gpu_memory_gb": None,
            "scheduler": None,
            "recommended_parallelism": 1,
        })
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
    return state


def write_state(repo_root: Path, state: dict[str, Any]) -> None:
    target_dir = state_dir(repo_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    state_file(repo_root).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    status_file(repo_root).write_text(status_markdown(state))


def default_state(repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "updated_at": now_iso(),
        "git": git_metadata(repo_root),
        "parts": [],
        "dependency_graph": {"edges": [], "unresolved_edges": []},
        "planning_workspace": {"root": str(plans_dir(repo_root)), "generated_at": None},
        "part_configs": {},
        "selection": {"part_id": None, "active_run_id": None},
        "runs": {},
        "reference": {"url": REFERENCE_REPO_URL, "path": None, "updated_at": None},
        "resources": {
            "detected_at": None,
            "cpus": None,
            "memory_gb": None,
            "gpus": [],
            "gpu_memory_gb": None,
            "scheduler": None,
            "recommended_parallelism": 1,
        },
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
) -> dict[str, Any]:
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

    if language == "python":
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


def write_planning_workspace(repo_root: Path, state: dict[str, Any]) -> None:
    root = plans_dir(repo_root)
    preserved_notes = load_preserved_plan_notes(root)
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    for part in state.get("parts", []):
        part_dir = root / PurePosixPath(part["id"])
        part_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "part_id": part["id"],
            "status": part["status"],
            "language": part["language"],
            "suggested_metric": part["suggested_metric"],
            "dependency_clarity": part["dependency_clarity"],
            "dependencies": part["dependencies"],
            "dependents": part["dependents"],
            "unresolved_dependencies": part["unresolved_dependencies"],
        }
        (part_dir / PLAN_METADATA_FILENAME).write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
        (part_dir / PLAN_DEPENDENCIES_FILENAME).write_text(render_part_dependencies(part))
        notes_path = part_dir / PLAN_NOTES_FILENAME
        notes_text = preserved_notes.get(part["id"], default_plan_notes(part))
        notes_path.write_text(notes_text)


def load_preserved_plan_notes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    notes: dict[str, str] = {}
    for path in root.rglob(PLAN_NOTES_FILENAME):
        relative = path.relative_to(root)
        part_id = relative.parent.as_posix()
        notes[part_id] = path.read_text()
    return notes


def render_part_dependencies(part: dict[str, Any]) -> str:
    lines = [
        f"# {part['id']}",
        "",
        f"- Status: `{part['status']}`",
        f"- Dependency clarity: `{part['dependency_clarity']}`",
        f"- Suggested metric: `{part['suggested_metric']['name']}`",
        "",
        "## Direct Dependencies",
    ]
    if part["dependencies"]:
        for dependency in part["dependencies"]:
            lines.append(f"- `{dependency}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Dependents"])
    if part["dependents"]:
        for dependent in part["dependents"]:
            lines.append(f"- `{dependent}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Unresolved Dependencies"])
    if part["unresolved_dependencies"]:
        for item in part["unresolved_dependencies"]:
            importance = "important" if item["important"] else "external"
            lines.append(f"- `{item['target']}` ({item['kind']}, {importance})")
            lines.append(f"  reason: {item['reason']}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def default_plan_notes(part: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Notes for {part['id']}",
            "",
            "- Optimization idea:",
            "- Metric confirmation:",
            "- Supporting dependency edits to watch:",
            "- Risks / open questions:",
            "",
        ]
    )


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
    if not config:
        return False
    metric = config.get("metric", {})
    execution = config.get("execution", {})
    return bool(
        metric.get("name")
        and metric.get("goal")
        and metric.get("command")
        and metric.get("regex")
        and execution.get("mode")
        and (execution.get("rounds") or execution.get("stop_rule"))
    )


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
    if not (execution.get("rounds") or execution.get("stop_rule")):
        missing.append("execution.rounds_or_stop_rule")
    return missing


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


def plans_dir(repo_root: Path) -> Path:
    return state_dir(repo_root) / PLANS_DIRNAME


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


def find_active_run(state: dict[str, Any], part_id: str) -> dict[str, Any] | None:
    active_id = state.get("selection", {}).get("active_run_id")
    if active_id:
        run = state.get("runs", {}).get(active_id)
        if run and run.get("part_id") == part_id and run.get("status") not in TERMINAL_RUN_STATUSES:
            return run
    for run in state.get("runs", {}).values():
        if run.get("part_id") == part_id and run.get("status") not in TERMINAL_RUN_STATUSES:
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
    run_id = build_run_id(part["id"])
    run_dir = runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    worktree_root = default_worktree_root(repo_root) / run_id
    worktree_root.mkdir(parents=True, exist_ok=True)

    base_ref = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()
    branch_prefix = f"autoresearch/{slugify(part['id'])}/{run_id}"
    seed = create_candidate_worktree(
        repo_root=repo_root,
        worktree_path=worktree_root / "seed",
        branch_name=f"{branch_prefix}/seed",
        base_ref=base_ref,
        candidate_id="seed",
        based_on=base_ref,
    )

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

    Path(run["results_path"]).write_text(
        "timestamp\trun_id\tcandidate_id\tstatus\tmetric_name\tmetric_value\tgoal\tcommit\tbranch\tworktree\tdescription\n"
    )
    Path(run["program_path"]).write_text(render_program(repo_root, run, part, config))

    if config["execution"].get("mode") in ("parallel", "wild"):
        parallelism = max(int(config["execution"].get("parallelism", 2)), 1)
        for _ in range(parallelism):
            run["candidates"].append(allocate_candidate(repo_root, run))

    state.setdefault("runs", {})[run_id] = run
    state.setdefault("selection", {})["active_run_id"] = run_id
    return run


def build_run_id(part_id: str) -> str:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{slugify(part_id)}"


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
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        metric_command,
        cwd=cwd,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    combined = completed.stdout + ("\n" if completed.stdout and completed.stderr else "") + completed.stderr
    metric_value = parse_metric_value(combined, metric_regex)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{candidate_id}-{timestamp}.log"
    log_path.write_text(
        "\n".join(
            [
                f"$ {metric_command}",
                "",
                completed.stdout,
                "",
                completed.stderr,
            ]
        )
    )
    return {
        "command": metric_command,
        "regex": metric_regex,
        "exit_code": completed.returncode,
        "metric_value": metric_value,
        "log_path": str(log_path),
        "recorded_at": now_iso(),
    }


def parse_metric_value(output: str, metric_regex: str) -> float | None:
    match = re.search(metric_regex, output, re.MULTILINE)
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
    commit = current_commit(Path(candidate["worktree_path"]))
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
        plans_root=str(plans_dir(repo_root)),
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
    best_metric = previous_best if previous_best is not None else run.get("best_metric")
    threshold = early_exit.get("threshold") or 0.0
    goal = run.get("metric", {}).get("goal") or "minimize"

    if metric_value is None or best_metric is None:
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
# Feature: Resource Detection
# ---------------------------------------------------------------------------


def detect_system_resources() -> dict[str, Any]:
    """Detect CPUs, memory, GPUs, and scheduler type."""
    cpus = os.cpu_count() or 1
    memory_gb = detect_system_memory_gb()
    gpus = detect_gpu_info()
    gpu_memory_gb = sum(g.get("memory_mb", 0) for g in gpus) / 1024 if gpus else None
    scheduler = detect_scheduler()
    recommended = recommend_parallelism(cpus, len(gpus))
    return {
        "detected_at": now_iso(),
        "cpus": cpus,
        "memory_gb": round(memory_gb, 2) if memory_gb else None,
        "gpus": gpus,
        "gpu_memory_gb": round(gpu_memory_gb, 2) if gpu_memory_gb else None,
        "scheduler": scheduler,
        "recommended_parallelism": recommended,
    }


def detect_system_memory_gb() -> float | None:
    """Detect total system memory in GB."""
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        try:
            text = meminfo.read_text()
            for line in text.splitlines():
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb / (1024 * 1024)
        except (OSError, ValueError, IndexError):
            pass
    if shutil.which("sysctl"):
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip()) / (1024 ** 3)
        except (OSError, ValueError):
            pass
    return None


def detect_gpu_info() -> list[dict[str, Any]]:
    """Detect GPUs via nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            return []
        gpus = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                gpus.append({"name": parts[0], "memory_mb": float(parts[1])})
        return gpus
    except (OSError, ValueError):
        return []


def detect_scheduler() -> str | None:
    """Check for cluster schedulers (slurm, pbs)."""
    for name, commands in SCHEDULER_COMMANDS.items():
        if all(shutil.which(cmd) for cmd in commands):
            return name
    return None


def recommend_parallelism(cpus: int, gpu_count: int) -> int:
    """Heuristic for default parallelism."""
    candidates = [cpus // 2] if cpus > 1 else [1]
    if gpu_count > 0:
        candidates.append(gpu_count)
    else:
        candidates.append(4)
    return max(1, min(min(candidates), 8))


def command_resources(args: argparse.Namespace) -> int:
    repo_root = detect_repo_root(Path(args.repo))
    resources = detect_system_resources()
    state = ensure_scanned(repo_root)
    state["resources"] = resources
    write_state(repo_root, state)

    interactive = resolve_interactive(args)
    if interactive:
        print(f"\nDetected resources:")
        print(f"  CPUs: {resources['cpus']}")
        print(f"  Memory: {resources['memory_gb']} GB")
        print(f"  GPUs: {len(resources['gpus'])}")
        if resources["gpus"]:
            for gpu in resources["gpus"]:
                print(f"    - {gpu['name']} ({gpu['memory_mb']} MB)")
        print(f"  Scheduler: {resources['scheduler'] or 'local'}")
        print(f"  Recommended parallelism: {resources['recommended_parallelism']}")
        if wizard_confirm("Override recommended parallelism?", default=False):
            resources["recommended_parallelism"] = wizard_int(
                "Parallelism", default=resources["recommended_parallelism"]
            )
            state["resources"] = resources
            write_state(repo_root, state)

    emit(resources, getattr(args, "json", False))
    return 0


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
# Feature: Wild Mode
# ---------------------------------------------------------------------------


def should_widen_search(run: dict[str, Any]) -> bool:
    """Check if improvement has stalled and wild mode should widen the search scope."""
    early_exit = run.get("early_exit", {})
    stalled = early_exit.get("rounds_without_improvement", 0)
    patience = early_exit.get("patience") or 3
    return stalled >= max(patience // 2, 1)


def plan_wild_changes(run: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Analyze metric flow to suggest which parameters to vary together."""
    max_simultaneous = config.get("execution", {}).get("wild_max_simultaneous") or 3
    stalled = run.get("early_exit", {}).get("rounds_without_improvement", 0)

    if stalled >= 3:
        strategy = "aggressive"
        reason = f"No improvement for {stalled} rounds; widening to {max_simultaneous} simultaneous changes."
    elif stalled >= 1:
        strategy = "moderate"
        max_simultaneous = min(max_simultaneous, 2)
        reason = f"Improvement slowing; trying {max_simultaneous} simultaneous changes."
    else:
        strategy = "conservative"
        max_simultaneous = 1
        reason = "Still improving; keeping single-parameter changes."

    return {
        "strategy": strategy,
        "max_simultaneous": max_simultaneous,
        "reason": reason,
    }


def format_wild_plan(plan: dict[str, Any]) -> str:
    """Format a human-readable summary of the wild mode strategy."""
    return (
        f"Wild mode [{plan['strategy']}]: {plan['reason']} "
        f"(max {plan['max_simultaneous']} simultaneous changes)"
    )


# ---------------------------------------------------------------------------
# Feature: Create
# ---------------------------------------------------------------------------


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

    num_candidates = args.candidates
    affected = identify_affected_parts(state, [part["id"]])

    metric_name = args.metric
    metric_goal = args.metric_goal
    metric_command = args.metric_command
    if interactive:
        metric_name = prompt_if_missing(metric_name, "Metric name")
        metric_goal = prompt_if_missing(metric_goal, "Metric goal [minimize|maximize]")
        metric_command = prompt_if_missing(metric_command, "Metric command")

    if not metric_name or not metric_goal or not metric_command:
        raise SystemExit("metric, metric-goal, and metric-command are required for create runs")

    config = merge_config(
        part=part,
        existing={},
        metric_name=metric_name,
        metric_goal=metric_goal,
        metric_command=metric_command,
        metric_regex=DEFAULT_METRIC_REGEX,
        mode="parallel",
        rounds=args.rounds,
        stop_rule=None,
        parallelism=num_candidates,
        entrypoint_type="part",
        entrypoint_path=part["id"],
        metric_preset=None,
        command_suggestion=None,
    )
    normalize_execution_defaults(config["execution"])
    state.setdefault("part_configs", {})[part["id"]] = config

    create_info = {
        "feature_description": feature_description,
        "num_approaches": num_candidates,
        "affected_parts": affected,
        "approach_labels": [f"approach-{chr(65 + i)}" for i in range(num_candidates)],
    }

    run = create_create_run(repo_root, state, part, config, create_info)
    state.setdefault("selection", {})["part_id"] = part["id"]
    state.setdefault("selection", {})["active_run_id"] = run["run_id"]
    write_state(repo_root, state)

    payload = {
        "run_id": run["run_id"],
        "run_type": "create",
        "part_id": part["id"],
        "feature": feature_description,
        "candidates": [c["candidate_id"] for c in run["candidates"]],
        "affected_parts": affected,
        "program_path": run["program_path"],
    }
    emit(payload, getattr(args, "json", False))
    return 0


def identify_affected_parts(state: dict[str, Any], target_part_ids: list[str]) -> list[str]:
    """Walk the dependency graph outward from target parts to find affected modules."""
    affected: set[str] = set()
    queue = list(target_part_ids)
    parts_by_id = {p["id"]: p for p in state.get("parts", [])}

    while queue:
        current = queue.pop(0)
        if current in affected:
            continue
        affected.add(current)
        part = parts_by_id.get(current)
        if part:
            for dep in part.get("dependents", []):
                if dep not in affected:
                    queue.append(dep)
            for dep in part.get("dependencies", []):
                if dep not in affected:
                    queue.append(dep)

    affected.discard(target_part_ids[0] if target_part_ids else "")
    return sorted(affected)


def create_create_run(
    repo_root: Path, state: dict[str, Any], part: dict[str, Any],
    config: dict[str, Any], create_info: dict[str, Any],
) -> dict[str, Any]:
    """Create a run with multiple candidate worktrees for comparing new feature approaches."""
    run_id = build_run_id(part["id"])
    run_dir = runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    worktree_root = default_worktree_root(repo_root) / run_id
    worktree_root.mkdir(parents=True, exist_ok=True)

    base_ref = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()
    branch_prefix = f"autoresearch/{slugify(part['id'])}/{run_id}"

    seed = create_candidate_worktree(
        repo_root=repo_root,
        worktree_path=worktree_root / "seed",
        branch_name=f"{branch_prefix}/seed",
        base_ref=base_ref,
        candidate_id="seed",
        based_on=base_ref,
    )

    run = {
        "run_id": run_id,
        "part_id": part["id"],
        "run_type": "create",
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
            "patience": None, "threshold": None,
            "rounds_without_improvement": 0, "triggered": False, "trigger_reason": None,
        },
        "create_info": create_info,
        "delete_info": None,
    }

    Path(run["results_path"]).write_text(
        "timestamp\trun_id\tcandidate_id\tstatus\tmetric_name\tmetric_value\tgoal\tcommit\tbranch\tworktree\tdescription\n"
    )

    # Create candidate worktrees for each approach
    for label in create_info["approach_labels"]:
        candidate = create_candidate_worktree(
            repo_root=repo_root,
            worktree_path=worktree_root / label,
            branch_name=f"{branch_prefix}/{label}",
            base_ref=base_ref,
            candidate_id=label,
            based_on=base_ref,
        )
        run["candidates"].append(candidate)

    Path(run["program_path"]).write_text(render_create_program(repo_root, run, part, config, create_info))
    state.setdefault("runs", {})[run_id] = run
    return run


def render_create_program(
    repo_root: Path, run: dict[str, Any], part: dict[str, Any],
    config: dict[str, Any], create_info: dict[str, Any],
) -> str:
    """Render a program.md for create runs."""
    lines = [
        f"# Create Run: {run['run_id']}",
        "",
        f"## Feature: {create_info['feature_description']}",
        "",
        f"Target part: `{part['id']}`",
        f"Approaches: {create_info['num_approaches']}",
        "",
        "## Affected Parts",
        "",
    ]
    for affected in create_info["affected_parts"]:
        lines.append(f"- `{affected}`")
    if not create_info["affected_parts"]:
        lines.append("- none identified")

    lines.extend([
        "",
        "## Metric",
        "",
        f"- Name: `{config['metric']['name']}`",
        f"- Goal: `{config['metric']['goal']}`",
        f"- Command: `{config['metric']['command']}`",
        "",
        "## Candidate Worktrees",
        "",
    ])
    for candidate in run["candidates"]:
        lines.append(f"- `{candidate['candidate_id']}`: `{candidate['worktree_path']}`")

    script_path = str(helper_script_path())
    lines.extend([
        "",
        "## Instructions",
        "",
        "1. Implement the feature differently in each approach worktree.",
        "2. Evaluate each approach:",
        "",
        f"```bash",
        f"python3 {script_path} evaluate --run-id {run['run_id']} --candidate <approach>",
        f"python3 {script_path} record --run-id {run['run_id']} --candidate <approach> --status auto --description \"<summary>\"",
        "```",
        "",
        "3. Compare results to find the approach with the best real capability ceiling.",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Feature: Delete
# ---------------------------------------------------------------------------


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

    metric_name = args.metric
    metric_goal = args.metric_goal
    metric_command = args.metric_command
    if interactive:
        metric_name = prompt_if_missing(metric_name, "Metric name")
        metric_goal = prompt_if_missing(metric_goal, "Metric goal [minimize|maximize]")
        metric_command = prompt_if_missing(metric_command, "Metric command")

    if not metric_name or not metric_goal or not metric_command:
        raise SystemExit("metric, metric-goal, and metric-command are required for delete runs")

    config = merge_config(
        part=part,
        existing={},
        metric_name=metric_name,
        metric_goal=metric_goal,
        metric_command=metric_command,
        metric_regex=DEFAULT_METRIC_REGEX,
        mode="sequential",
        rounds=args.rounds,
        stop_rule=None,
        parallelism=1,
        entrypoint_type="part",
        entrypoint_path=part["id"],
        metric_preset=None,
        command_suggestion=None,
    )
    normalize_execution_defaults(config["execution"])

    delete_info = {
        "deleted_part_id": part["id"],
        "dependent_parts": dependents,
        "pre_deletion_metrics": None,
    }

    run = create_delete_run(repo_root, state, part, config, delete_info)
    state.setdefault("selection", {})["part_id"] = part["id"]
    state.setdefault("selection", {})["active_run_id"] = run["run_id"]
    write_state(repo_root, state)

    payload = {
        "run_id": run["run_id"],
        "run_type": "delete",
        "deleted_part": part["id"],
        "dependent_parts": dependents,
        "program_path": run["program_path"],
        "candidates": [c["candidate_id"] for c in run["candidates"]],
    }
    emit(payload, getattr(args, "json", False))
    return 0


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
        git_run(worktree_path, ["add", part_id], check=False)
        git_run(
            worktree_path,
            ["commit", "-m", f"autoresearch: delete {part_id}"],
            check=False,
        )


def create_delete_run(
    repo_root: Path, state: dict[str, Any], part: dict[str, Any],
    config: dict[str, Any], delete_info: dict[str, Any],
) -> dict[str, Any]:
    """Create a run where the seed worktree has the target part removed."""
    run_id = build_run_id(part["id"])
    run_dir = runs_dir(repo_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    worktree_root = default_worktree_root(repo_root) / run_id
    worktree_root.mkdir(parents=True, exist_ok=True)

    base_ref = git_stdout(repo_root, ["rev-parse", "HEAD"]).strip()
    branch_prefix = f"autoresearch/{slugify(part['id'])}/{run_id}"

    seed = create_candidate_worktree(
        repo_root=repo_root,
        worktree_path=worktree_root / "seed",
        branch_name=f"{branch_prefix}/seed",
        base_ref=base_ref,
        candidate_id="seed",
        based_on=base_ref,
    )

    # Apply the deletion in the seed worktree
    apply_deletion_to_worktree(Path(seed["worktree_path"]), part["id"])

    run = {
        "run_id": run_id,
        "part_id": part["id"],
        "run_type": "delete",
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
            "patience": None, "threshold": None,
            "rounds_without_improvement": 0, "triggered": False, "trigger_reason": None,
        },
        "create_info": None,
        "delete_info": delete_info,
    }

    Path(run["results_path"]).write_text(
        "timestamp\trun_id\tcandidate_id\tstatus\tmetric_name\tmetric_value\tgoal\tcommit\tbranch\tworktree\tdescription\n"
    )
    Path(run["program_path"]).write_text(render_delete_program(repo_root, run, part, config, delete_info))
    state.setdefault("runs", {})[run_id] = run
    return run


def render_delete_program(
    repo_root: Path, run: dict[str, Any], part: dict[str, Any],
    config: dict[str, Any], delete_info: dict[str, Any],
) -> str:
    """Render a program.md for delete runs."""
    lines = [
        f"# Delete Run: {run['run_id']}",
        "",
        f"Deleted part: `{delete_info['deleted_part_id']}`",
        "",
        "## Affected Dependents",
        "",
    ]
    for dep in delete_info["dependent_parts"]:
        lines.append(f"- `{dep}`")
    if not delete_info["dependent_parts"]:
        lines.append("- none identified")

    lines.extend([
        "",
        "## Metric",
        "",
        f"- Name: `{config['metric']['name']}`",
        f"- Goal: `{config['metric']['goal']}`",
        f"- Command: `{config['metric']['command']}`",
        "",
        "## Seed Worktree",
        "",
        f"The seed worktree at `{run['candidates'][0]['worktree_path']}` already has `{delete_info['deleted_part_id']}` removed.",
        "",
        "## Instructions",
        "",
        "1. Fix broken imports and references in dependent parts within the seed worktree.",
        "2. Evaluate the baseline after fixing:",
        "",
    ])
    script_path = str(helper_script_path())
    lines.extend([
        f"```bash",
        f"python3 {script_path} evaluate --run-id {run['run_id']} --candidate seed",
        f"python3 {script_path} record --run-id {run['run_id']} --candidate seed --status auto --description \"post-deletion baseline\"",
        "```",
        "",
        "3. Allocate candidates to optimize dependent parameters:",
        "",
        f"```bash",
        f"python3 {script_path} allocate --run-id {run['run_id']}",
        "```",
        "",
        "4. Stop when the configured rounds or stop rule is satisfied.",
        "",
    ])
    return "\n".join(lines)
