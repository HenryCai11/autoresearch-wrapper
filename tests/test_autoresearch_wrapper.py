from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autoresearch_wrapper.core import (
    DEFAULT_METRIC_REGEX,
    check_early_exit,
    detect_system_resources,
    find_delete_dependents,
    format_monitor_update,
    get_candidate,
    group_parts_by_directory,
    group_parts_by_language,
    identify_affected_parts,
    load_state,
    main,
    migrate_state,
    mkdir_lock,
    normalize_entry_argv,
    parse_metric_value,
    plan_wild_changes,
    plans_dir,
    recommend_parallelism,
    render_dependency_tree,
    should_widen_search,
    state_dir,
    status_markdown,
    wizard_select,
    write_state,
)


class AutoresearchWrapperTests(unittest.TestCase):
    def make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="autoresearch-wrapper-"))
        subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp,
            check=True,
            capture_output=True,
            text=True,
        )
        return tmp

    def commit_all(self, repo: Path, message: str = "init") -> None:
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_scan_marks_clear_metric_as_surely_optimizable(self) -> None:
        repo = self.make_repo()
        (repo / "README.md").write_text("The benchmark tracks api latency and p95.\n")
        (repo / "src").mkdir()
        (repo / "src" / "helpers.py").write_text("def helper():\n    return 1\n")
        (repo / "src" / "api.py").write_text("# TODO optimize latency for requests\n")
        self.commit_all(repo)

        (repo / "src" / "api.py").write_text(
            "from .helpers import helper\n\n# TODO optimize latency for requests\n"
        )
        self.commit_all(repo, "add local dependency")

        main(["scan", "--repo", str(repo)])
        state = load_state(repo)
        part = next(part for part in state["parts"] if part["id"] == "src/api.py")
        helpers = next(part for part in state["parts"] if part["id"] == "src/helpers.py")

        self.assertEqual(part["status"], "surely optimizable")
        self.assertEqual(part["suggested_metric"]["name"], "latency_ms")
        self.assertEqual(part["dependencies"], ["src/helpers.py"])
        self.assertEqual(part["dependency_clarity"], "clear")
        self.assertEqual(helpers["dependents"], ["src/api.py"])
        self.assertTrue((plans_dir(repo) / "src" / "api.py" / "metadata.json").exists())
        self.assertTrue((plans_dir(repo) / "src" / "api.py" / "dependencies.md").exists())
        self.assertTrue((plans_dir(repo) / "src" / "api.py" / "notes.md").exists())
        self.assertIn("## Dependency Table", status_markdown(state))

    def test_configure_persists_ready_config(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo)])
        main(
            [
                "configure",
                "--repo",
                str(repo),
                "--part",
                "module.py",
                "--metric",
                "runtime_seconds",
                "--metric-command",
                "python -c \"print('METRIC=1.0')\"",
                "--metric-goal",
                "minimize",
                "--mode",
                "sequential",
                "--rounds",
                "3",
            ]
        )

        state = load_state(repo)
        config = state["part_configs"]["module.py"]
        self.assertEqual(config["metric"]["name"], "runtime_seconds")
        self.assertEqual(config["execution"]["mode"], "sequential")
        self.assertTrue((state_dir(repo) / "STATUS.md").exists())

    def test_run_allocate_evaluate_and_record(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n\ndef main():\n    return helper.VALUE\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo)])
        main(
            [
                "configure",
                "--repo",
                str(repo),
                "--part",
                "module.py",
                "--metric",
                "runtime_seconds",
                "--metric-command",
                "python -c \"print('METRIC=1.0')\"",
                "--metric-goal",
                "minimize",
                "--mode",
                "sequential",
                "--rounds",
                "1",
            ]
        )

        main(["run", "--repo", str(repo), "--part", "module.py"])
        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]
        run = state["runs"][run_id]
        self.assertTrue(Path(run["candidates"][0]["worktree_path"]).exists())

        main(["evaluate", "--repo", str(repo), "--run-id", run_id, "--candidate", "seed"])
        main(
            [
                "record",
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--candidate",
                "seed",
                "--status",
                "auto",
                "--description",
                "baseline",
            ]
        )
        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        main(
            [
                "evaluate",
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--candidate",
                "candidate-001",
            ]
        )
        main(
            [
                "record",
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--candidate",
                "candidate-001",
                "--status",
                "auto",
                "--description",
                "same metric as baseline",
            ]
        )

        state = load_state(repo)
        run = state["runs"][run_id]
        candidate = next(item for item in run["candidates"] if item["candidate_id"] == "candidate-001")

        self.assertEqual(candidate["result"]["status"], "discard")
        self.assertEqual(run["rounds_completed"], 1)
        results = Path(run["results_path"]).read_text()
        self.assertIn("candidate-001", results)

    def test_flow_shows_metric_history_and_plot(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n\ndef main():\n    return helper.VALUE\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo)])
        main(
            [
                "configure",
                "--repo",
                str(repo),
                "--part",
                "module.py",
                "--metric",
                "runtime_seconds",
                "--metric-command",
                "python -c \"print('METRIC=1.0')\"",
                "--metric-goal",
                "minimize",
                "--mode",
                "sequential",
                "--rounds",
                "2",
            ]
        )

        main(["run", "--repo", str(repo), "--part", "module.py"])
        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]

        main(
            [
                "record",
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--candidate",
                "seed",
                "--metric-value",
                "1.0",
                "--description",
                "baseline",
            ]
        )
        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        main(
            [
                "record",
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--candidate",
                "candidate-001",
                "--metric-value",
                "0.75",
                "--description",
                "improved candidate",
            ]
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["flow", "--repo", str(repo), "--run-id", run_id, "--width", "12"])
        rendered = output.getvalue()

        self.assertIn("Metric Flow", rendered)
        self.assertIn("seed=1.000000 -> candidate-001=0.750000", rendered)
        self.assertIn("candidate-001", rendered)
        self.assertIn("############", rendered)

        state = load_state(repo)
        status = status_markdown(state)
        self.assertIn("Metric flow: seed=1.000000 -> candidate-001=0.750000", status)
        self.assertIn("Best-so-far: seed=1.000000 -> candidate-001=0.750000", status)

    def test_run_blocks_when_dependency_boundary_is_unclear(self) -> None:
        repo = self.make_repo()
        (repo / "README.md").write_text("The benchmark tracks api latency and p95.\n")
        (repo / "pkg").mkdir()
        (repo / "pkg" / "__init__.py").write_text("")
        (repo / "pkg" / "api.py").write_text(
            "from .missing import helper\n\n# TODO optimize latency for requests\n"
        )
        self.commit_all(repo)

        main(["scan", "--repo", str(repo)])
        state = load_state(repo)
        part = next(part for part in state["parts"] if part["id"] == "pkg/api.py")
        self.assertEqual(part["status"], "probably optimizable")
        self.assertTrue(part["unresolved_dependencies"])

        main(
            [
                "configure",
                "--repo",
                str(repo),
                "--part",
                "pkg/api.py",
                "--metric",
                "latency_ms",
                "--metric-command",
                "python -c \"print('METRIC=1.0')\"",
                "--metric-goal",
                "minimize",
                "--mode",
                "sequential",
                "--rounds",
                "1",
            ]
        )

        with self.assertRaises(SystemExit) as exc:
            main(["run", "--repo", str(repo), "--part", "pkg/api.py"])
        self.assertIn("dependency graph is incomplete", str(exc.exception))

    def test_wrap_shorthand_creates_script_stub(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "bench.py").write_text("import helper\nprint(helper.VALUE)\n")
        self.commit_all(repo)

        main(["bench.py", "--repo", str(repo)])
        state = load_state(repo)
        config = state["part_configs"]["bench.py"]
        part = next(part for part in state["parts"] if part["id"] == "bench.py")

        self.assertEqual(state["selection"]["part_id"], "bench.py")
        self.assertEqual(config["entrypoint"]["type"], "script")
        self.assertEqual(config["metric"]["preset"], "runtime_seconds")
        self.assertIsNone(config["metric"]["command"])
        self.assertIn("preset-metric", config["metric"]["command_suggestion"])
        self.assertEqual(config["execution"]["mode"], "sequential")
        self.assertEqual(config["execution"]["rounds"], 3)
        self.assertFalse(part["ready"])

    def test_wrap_suggested_command_can_run_evaluate(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "bench.py").write_text("import helper\nprint(helper.VALUE)\n")
        self.commit_all(repo)

        main(["wrap", "--repo", str(repo), "bench.py"])
        main(
            [
                "configure",
                "--repo",
                str(repo),
                "--part",
                "bench.py",
                "--use-suggested-command",
            ]
        )

        state = load_state(repo)
        config = state["part_configs"]["bench.py"]
        self.assertEqual(config["metric"]["preset"], "runtime_seconds")
        self.assertIsNotNone(config["metric"]["command"])

        main(["run", "--repo", str(repo), "--part", "bench.py"])
        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]
        main(["evaluate", "--repo", str(repo), "--run-id", run_id, "--candidate", "seed"])

        state = load_state(repo)
        run = state["runs"][run_id]
        seed = next(item for item in run["candidates"] if item["candidate_id"] == "seed")
        self.assertEqual(seed["latest_evaluation"]["exit_code"], 0)
        self.assertIsNotNone(seed["latest_evaluation"]["metric_value"])

    # -----------------------------------------------------------------------
    # Schema migration
    # -----------------------------------------------------------------------

    def test_migrate_v1_to_v2_adds_resources(self) -> None:
        v1_state = {
            "schema_version": 1,
            "repo_root": "/tmp/test",
            "parts": [],
            "runs": {},
            "part_configs": {},
        }
        migrated = migrate_state(dict(v1_state), Path("/tmp/test"))
        self.assertEqual(migrated["schema_version"], 2)
        self.assertIn("resources", migrated)
        self.assertIsNone(migrated["resources"]["detected_at"])
        self.assertEqual(migrated["resources"]["recommended_parallelism"], 1)

    def test_migrate_v1_backfills_run_fields(self) -> None:
        v1_state = {
            "schema_version": 1,
            "repo_root": "/tmp/test",
            "parts": [],
            "runs": {
                "test-run": {
                    "run_id": "test-run",
                    "status": "running",
                }
            },
            "part_configs": {
                "module.py": {
                    "metric": {"name": "runtime_seconds"},
                    "execution": {"mode": "sequential", "rounds": 3},
                }
            },
        }
        migrated = migrate_state(dict(v1_state), Path("/tmp/test"))
        run = migrated["runs"]["test-run"]
        self.assertEqual(run["run_type"], "optimize")
        self.assertIn("early_exit", run)
        self.assertFalse(run["early_exit"]["triggered"])
        config = migrated["part_configs"]["module.py"]
        self.assertIn("early_exit_patience", config["execution"])
        self.assertIn("wild_max_simultaneous", config["execution"])

    # -----------------------------------------------------------------------
    # Resource detection
    # -----------------------------------------------------------------------

    def test_resources_detects_cpu_count(self) -> None:
        resources = detect_system_resources()
        self.assertIsInstance(resources["cpus"], int)
        self.assertGreater(resources["cpus"], 0)
        self.assertIsNotNone(resources["detected_at"])

    def test_recommended_parallelism_bounds(self) -> None:
        self.assertEqual(recommend_parallelism(1, 0), 1)
        self.assertGreaterEqual(recommend_parallelism(16, 0), 1)
        self.assertLessEqual(recommend_parallelism(16, 0), 8)
        self.assertGreaterEqual(recommend_parallelism(4, 2), 1)
        self.assertLessEqual(recommend_parallelism(4, 2), 8)

    def test_resources_persists_to_state(self) -> None:
        repo = self.make_repo()
        (repo / "module.py").write_text("x = 1\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main(["resources", "--repo", str(repo), "--no-interactive"])
        state = load_state(repo)
        self.assertIsNotNone(state["resources"]["detected_at"])
        self.assertGreater(state["resources"]["cpus"], 0)

    # -----------------------------------------------------------------------
    # Early exit
    # -----------------------------------------------------------------------

    def test_early_exit_triggers_after_patience_exceeded(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main([
            "configure", "--repo", str(repo), "--part", "module.py",
            "--metric", "runtime_seconds",
            "--metric-command", "python -c \"print('METRIC=1.0')\"",
            "--metric-goal", "minimize", "--mode", "sequential",
            "--rounds", "10", "--early-exit-patience", "2",
        ])
        main(["run", "--repo", str(repo), "--part", "module.py", "--no-interactive"])
        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]

        # Record seed baseline
        main(["record", "--repo", str(repo), "--run-id", run_id,
              "--candidate", "seed", "--metric-value", "1.0", "--description", "baseline"])

        # Round 1: no improvement
        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        main(["record", "--repo", str(repo), "--run-id", run_id,
              "--candidate", "candidate-001", "--metric-value", "1.0", "--description", "same"])

        # Round 2: no improvement
        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        main(["record", "--repo", str(repo), "--run-id", run_id,
              "--candidate", "candidate-002", "--metric-value", "1.1", "--description", "worse"])

        state = load_state(repo)
        run = state["runs"][run_id]
        self.assertEqual(run["status"], "early_exit")
        self.assertTrue(run["early_exit"]["triggered"])
        self.assertIn("no improvement", run["early_exit"]["trigger_reason"])

    def test_early_exit_does_not_trigger_when_improving(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main([
            "configure", "--repo", str(repo), "--part", "module.py",
            "--metric", "runtime_seconds",
            "--metric-command", "python -c \"print('METRIC=1.0')\"",
            "--metric-goal", "minimize", "--mode", "sequential",
            "--rounds", "5", "--early-exit-patience", "2",
        ])
        main(["run", "--repo", str(repo), "--part", "module.py", "--no-interactive"])
        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]

        main(["record", "--repo", str(repo), "--run-id", run_id,
              "--candidate", "seed", "--metric-value", "1.0", "--description", "baseline"])
        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        main(["record", "--repo", str(repo), "--run-id", run_id,
              "--candidate", "candidate-001", "--metric-value", "0.5", "--description", "improved"])

        state = load_state(repo)
        run = state["runs"][run_id]
        self.assertEqual(run["status"], "running")
        self.assertFalse(run["early_exit"]["triggered"])

    def test_early_exit_disabled_by_default(self) -> None:
        run = {
            "early_exit": {"patience": None, "threshold": None, "rounds_without_improvement": 5},
        }
        result = check_early_exit(run)
        self.assertFalse(result["should_exit"])

    # -----------------------------------------------------------------------
    # Monitor
    # -----------------------------------------------------------------------

    def test_monitor_format_includes_key_fields(self) -> None:
        run = {
            "run_id": "test-run",
            "status": "running",
            "rounds_completed": 2,
            "execution": {"rounds": 5},
            "best_metric": 0.75,
            "early_exit": {"patience": 3, "rounds_without_improvement": 1},
        }
        output = format_monitor_update(run, 1)
        self.assertIn("status=running", output)
        self.assertIn("rounds=2/5", output)
        self.assertIn("stalled=1/3", output)

    # -----------------------------------------------------------------------
    # Wild mode
    # -----------------------------------------------------------------------

    def test_wild_mode_sets_defaults(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main([
            "configure", "--repo", str(repo), "--part", "module.py",
            "--metric", "runtime_seconds",
            "--metric-command", "python -c \"print('METRIC=1.0')\"",
            "--metric-goal", "minimize", "--mode", "wild", "--rounds", "3",
        ])

        state = load_state(repo)
        config = state["part_configs"]["module.py"]
        self.assertEqual(config["execution"]["mode"], "wild")
        self.assertEqual(config["execution"]["wild_max_simultaneous"], 3)
        self.assertEqual(config["execution"]["parallelism"], 2)

    def test_should_widen_search_when_stalled(self) -> None:
        run = {
            "early_exit": {"patience": 4, "rounds_without_improvement": 3},
        }
        self.assertTrue(should_widen_search(run))

    def test_should_not_widen_when_improving(self) -> None:
        run = {
            "early_exit": {"patience": 4, "rounds_without_improvement": 0},
        }
        self.assertFalse(should_widen_search(run))

    def test_plan_wild_changes_strategy(self) -> None:
        run = {"early_exit": {"rounds_without_improvement": 5}}
        config = {"execution": {"wild_max_simultaneous": 4}}
        plan = plan_wild_changes(run, config)
        self.assertEqual(plan["strategy"], "aggressive")
        self.assertEqual(plan["max_simultaneous"], 4)

    # -----------------------------------------------------------------------
    # Create
    # -----------------------------------------------------------------------

    def test_create_identifies_affected_parts(self) -> None:
        repo = self.make_repo()
        (repo / "a.py").write_text("def a(): pass\n")
        (repo / "b.py").write_text("import a\ndef b(): pass\n")
        (repo / "c.py").write_text("import b\ndef c(): pass\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        state = load_state(repo)
        affected = identify_affected_parts(state, ["a.py"])
        self.assertIn("b.py", affected)

    def test_create_run_creates_multiple_worktrees(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main([
            "create", "--repo", str(repo), "--part", "module.py",
            "--feature", "add caching", "--candidates", "2",
            "--metric", "runtime_seconds",
            "--metric-command", "python -c \"print('METRIC=1.0')\"",
            "--metric-goal", "minimize", "--no-interactive",
        ])

        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]
        run = state["runs"][run_id]
        self.assertEqual(run["run_type"], "create")
        self.assertIsNotNone(run["create_info"])
        self.assertEqual(run["create_info"]["feature_description"], "add caching")
        # control + 2 approaches, each with its own setup worktree
        self.assertEqual(
            [arm["arm_id"] for arm in run["arms"]], ["control", "approach-A", "approach-B"]
        )
        for arm in run["arms"]:
            self.assertTrue(Path(arm["setup"]["worktree_path"]).exists(), arm["arm_id"])

    # -----------------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------------

    def test_delete_finds_transitive_dependents(self) -> None:
        repo = self.make_repo()
        (repo / "a.py").write_text("def a(): pass\n")
        (repo / "b.py").write_text("import a\ndef b(): pass\n")
        (repo / "c.py").write_text("import b\ndef c(): pass\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        state = load_state(repo)
        dependents = find_delete_dependents(state, "a.py")
        self.assertIn("b.py", dependents)
        self.assertIn("c.py", dependents)

    def test_delete_run_removes_file_in_worktree(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n# optimize this runtime path\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        main([
            "delete", "--repo", str(repo), "--part", "helper.py",
            "--metric", "runtime_seconds",
            "--metric-command", "python -c \"print('METRIC=1.0')\"",
            "--metric-goal", "minimize", "--no-interactive",
        ])

        state = load_state(repo)
        run_id = state["selection"]["active_run_id"]
        run = state["runs"][run_id]
        self.assertEqual(run["run_type"], "delete")
        self.assertIsNotNone(run["delete_info"])
        self.assertEqual(run["delete_info"]["deleted_part_id"], "helper.py")
        self.assertIn("module.py", run["delete_info"]["dependent_parts"])
        self.assertEqual([arm["arm_id"] for arm in run["arms"]], ["control", "deleted"])
        # The deleted arm's setup worktree has the file removed; control keeps it.
        deleted = next(arm for arm in run["arms"] if arm["arm_id"] == "deleted")
        control = next(arm for arm in run["arms"] if arm["arm_id"] == "control")
        self.assertFalse((Path(deleted["setup"]["worktree_path"]) / "helper.py").exists())
        self.assertTrue((Path(control["setup"]["worktree_path"]) / "helper.py").exists())

    def test_delete_blocks_if_part_not_found(self) -> None:
        repo = self.make_repo()
        (repo / "module.py").write_text("x = 1\n")
        self.commit_all(repo)

        main(["scan", "--repo", str(repo), "--no-interactive"])
        with self.assertRaises(SystemExit) as exc:
            main([
                "delete", "--repo", str(repo), "--part", "nonexistent.py",
                "--metric", "x", "--metric-command", "echo 1",
                "--metric-goal", "minimize", "--no-interactive",
            ])
        self.assertIn("unable to resolve part", str(exc.exception))

    def test_scan_default_focuses_on_core_modules(self) -> None:
        repo = self.make_repo()
        (repo / "src").mkdir()
        (repo / "tests").mkdir()
        (repo / "scripts").mkdir()
        (repo / "src" / "helpers.py").write_text("def helper():\n    return 1\n")
        (repo / "src" / "api.py").write_text(
            "from .helpers import helper\n\n# optimize latency in this hot path\n"
        )
        (repo / "tests" / "test_api.py").write_text("from src.api import helper\n")
        (repo / "scripts" / "bench.py").write_text("print('benchmark helper')\n")
        self.commit_all(repo)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["scan", "--repo", str(repo), "--no-interactive"])
        rendered = output.getvalue()

        self.assertIn("Core functionality focus:", rendered)
        self.assertIn("Focused dependency graph:", rendered)
        self.assertIn("src/api.py", rendered)
        self.assertIn("Use --full-summary", rendered)
        self.assertNotIn("tests/test_api.py [", rendered)
        self.assertNotIn("scripts/bench.py [", rendered)

    def test_scan_full_summary_shows_all_parts(self) -> None:
        repo = self.make_repo()
        (repo / "src").mkdir()
        (repo / "tests").mkdir()
        (repo / "scripts").mkdir()
        (repo / "src" / "helpers.py").write_text("def helper():\n    return 1\n")
        (repo / "src" / "api.py").write_text(
            "from .helpers import helper\n\n# optimize latency in this hot path\n"
        )
        (repo / "tests" / "test_api.py").write_text("from src.api import helper\n")
        (repo / "scripts" / "bench.py").write_text("print('benchmark helper')\n")
        self.commit_all(repo)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["scan", "--repo", str(repo), "--no-interactive", "--full-summary"])
        rendered = output.getvalue()

        self.assertIn("By language:", rendered)
        self.assertIn("By directory:", rendered)
        self.assertIn("Module dependency graph:", rendered)
        self.assertIn("tests/test_api.py", rendered)
        self.assertIn("scripts/bench.py", rendered)

    def test_scan_wizard_defaults_to_core_functionality(self) -> None:
        repo = self.make_repo()
        (repo / "src").mkdir()
        (repo / "tests").mkdir()
        (repo / "src" / "helpers.py").write_text("def helper():\n    return 1\n")
        (repo / "src" / "api.py").write_text(
            "from .helpers import helper\n\n# optimize latency in this hot path\n"
        )
        (repo / "tests" / "test_api.py").write_text("from src.api import helper\n")
        self.commit_all(repo)

        prompts: list[tuple[str, list[str], str | None]] = []

        def fake_wizard(label: str, options: list[str], default: str | None = None) -> str:
            prompts.append((label, options, default))
            return default or options[0]

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with mock.patch("autoresearch_wrapper.core.resolve_interactive", return_value=True):
                with mock.patch("autoresearch_wrapper.core.wizard_select", side_effect=fake_wizard):
                    main(["scan", "--repo", str(repo)])

        first_prompt = prompts[0]
        self.assertEqual(first_prompt[0], "Which functionality area do you want to improve?")
        self.assertIsNotNone(first_prompt[2])
        self.assertTrue(first_prompt[2].startswith("best-defined optimization targets ("))
        self.assertTrue(any("latency-sensitive functionality" in option for option in first_prompt[1]))

    def test_no_args_always_defaults_to_wizard(self) -> None:
        with mock.patch("autoresearch_wrapper.core.is_interactive_default", return_value=True):
            self.assertEqual(normalize_entry_argv([]), ["wizard"])
        with mock.patch("autoresearch_wrapper.core.is_interactive_default", return_value=False):
            self.assertEqual(normalize_entry_argv([]), ["wizard"])

    def test_skill_docs_route_bare_invocation_to_wizard(self) -> None:
        skill_files = [
            REPO_ROOT / "SKILL.md",
            REPO_ROOT / "skills" / "autoresearch-wrapper" / "SKILL.md",
            REPO_ROOT
            / "plugins"
            / "autoresearch-wrapper"
            / "skills"
            / "autoresearch-wrapper"
            / "SKILL.md",
        ]
        for path in skill_files:
            text = path.read_text()
            self.assertIn(
                "If invoked with no arguments (just `/autoresearch-wrapper` or `$autoresearch-wrapper`), "
                "route to the end-to-end wizard:",
                text,
                str(path),
            )
            self.assertTrue(
                'bash "$AUTORESEARCH_RUNNER" wizard' in text
                or 'python3 "$AUTORESEARCH_ROOT/scripts/autoresearch_wrapper.py" wizard' in text
                or "python3 scripts/autoresearch_wrapper.py wizard" in text,
                str(path),
            )

    def test_skill_launchers_find_cli_from_multiple_skill_trees(self) -> None:
        repo = self.make_repo()
        (repo / "module.py").write_text("print('ok')\n")
        self.commit_all(repo)

        # A user-level symlinked install, as Codex (~/.agents/skills) or Claude Code would use.
        home = Path(tempfile.mkdtemp(prefix="autoresearch-home-"))
        (home / ".agents" / "skills").mkdir(parents=True)
        installed = home / ".agents" / "skills" / "autoresearch-wrapper-run"
        installed.symlink_to(REPO_ROOT / "skills" / "autoresearch-wrapper-run", target_is_directory=True)

        launchers = [
            REPO_ROOT / ".claude" / "skills" / "autoresearch-wrapper" / "run.sh",
            REPO_ROOT / ".agents" / "skills" / "autoresearch-wrapper" / "run.sh",
            REPO_ROOT / "skills" / "autoresearch-wrapper" / "run.sh",
            REPO_ROOT / "run.sh",  # repo root installed as a single skill
            installed / "run.sh",
            REPO_ROOT
            / "plugins"
            / "autoresearch-wrapper"
            / "skills"
            / "autoresearch-wrapper"
            / "run.sh",
        ]
        for launcher in launchers:
            result = subprocess.run(
                ["bash", str(launcher), "status", "--repo", str(repo), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertIn("parts", payload, str(launcher))

    def test_skills_have_a_single_source(self) -> None:
        skills_root = REPO_ROOT / "skills"
        for link in (REPO_ROOT / ".claude" / "skills", REPO_ROOT / ".agents" / "skills"):
            self.assertTrue(link.is_symlink(), str(link))
            self.assertEqual(link.resolve(), skills_root.resolve(), str(link))
        # The root SKILL.md (repo installed as one skill) is a generated copy, not a second source.
        self.assertEqual(
            (REPO_ROOT / "SKILL.md").read_bytes(),
            (skills_root / "autoresearch-wrapper" / "SKILL.md").read_bytes(),
            "root SKILL.md drifted; run scripts/sync_claude_plugin.py",
        )

        # The packaged plugin is a generated copy; it must not drift from skills/.
        plugin_skills = REPO_ROOT / "plugins" / "autoresearch-wrapper" / "skills"
        source_files = sorted(p.relative_to(skills_root) for p in skills_root.rglob("*") if p.is_file())
        plugin_files = sorted(p.relative_to(plugin_skills) for p in plugin_skills.rglob("*") if p.is_file())
        self.assertEqual(source_files, plugin_files)
        for relative in source_files:
            self.assertEqual(
                (skills_root / relative).read_bytes(),
                (plugin_skills / relative).read_bytes(),
                f"{relative} drifted; run scripts/sync_claude_plugin.py",
            )

        for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            text = (skill_dir / "SKILL.md").read_text()
            self.assertIn(f"name: {skill_dir.name}\n", text, skill_dir.name)
            # Each launcher block must look for its own folder, in Claude and Codex locations.
            for location in (f".agents/skills/{skill_dir.name}", f".claude/skills/{skill_dir.name}"):
                self.assertIn(location, text, skill_dir.name)
            self.assertTrue((skill_dir / "run.sh").is_file(), skill_dir.name)

    def test_marketplace_versions_and_runtime_files_stay_aligned(self) -> None:
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text())
        packaged_plugin = json.loads(
            (REPO_ROOT / "plugins" / "autoresearch-wrapper" / ".claude-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(marketplace["metadata"]["version"], packaged_plugin["version"])
        self.assertEqual(marketplace["plugins"][0]["version"], packaged_plugin["version"])
        self.assertTrue(
            (REPO_ROOT / "plugins" / "autoresearch-wrapper" / "scripts" / "autoresearch_wrapper.py").is_file()
        )
        self.assertTrue(
            (REPO_ROOT / "plugins" / "autoresearch-wrapper" / "autoresearch_wrapper" / "core.py").is_file()
        )

    def test_wizard_runs_end_to_end(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text(
            "import helper\n# optimize this runtime path for latency\n"
        )
        self.commit_all(repo)

        def fake_select(label: str, options: list[str], default: str | None = None) -> str:
            if label == "Which functionality area do you want to improve?":
                return default or options[0]
            if label == "Select a part to optimize":
                return "module.py"
            if label == "Metric goal":
                return "minimize"
            if label == "Execution mode":
                return "sequential"
            return default or options[0]

        def fake_input(label: str, default: str | None = None) -> str:
            if label == "Metric command":
                return "python -c \"print('METRIC=1.0')\""
            return default or "runtime_seconds"

        def fake_int(label: str, default: int | None = None) -> int:
            if label == "Rounds":
                return 2
            return default or 2

        def fake_confirm(label: str, default: bool = True) -> bool:
            if label == "Enable early exit?":
                return False
            if label == "Start the run now?":
                return True
            return default

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with mock.patch("autoresearch_wrapper.core.wizard_select", side_effect=fake_select):
                with mock.patch("autoresearch_wrapper.core.wizard_input", side_effect=fake_input):
                    with mock.patch("autoresearch_wrapper.core.wizard_int", side_effect=fake_int):
                        with mock.patch(
                            "autoresearch_wrapper.core.wizard_optional_input", return_value=None
                        ):
                            with mock.patch(
                                "autoresearch_wrapper.core.wizard_optional_float", return_value=None
                            ):
                                with mock.patch(
                                    "autoresearch_wrapper.core.wizard_confirm",
                                    side_effect=fake_confirm,
                                ):
                                    main(["wizard", "--repo", str(repo), "--interactive"])

        rendered = output.getvalue()
        self.assertIn("Run started:", rendered)
        state = load_state(repo)
        self.assertEqual(state["selection"]["part_id"], "module.py")
        self.assertIsNotNone(state["selection"]["active_run_id"])
        config = state["part_configs"]["module.py"]
        self.assertEqual(config["metric"]["name"], "latency_ms")
        self.assertEqual(config["execution"]["mode"], "sequential")
        self.assertEqual(config["execution"]["rounds"], 2)

    # -----------------------------------------------------------------------
    # Wizard (basic unit tests, not interactive)
    # -----------------------------------------------------------------------

    def test_wizard_skipped_when_not_interactive(self) -> None:
        """Scan with --no-interactive should not prompt even with multiple parts."""
        repo = self.make_repo()
        (repo / "a.py").write_text("# optimize latency\n")
        (repo / "b.py").write_text("# optimize throughput\n")
        self.commit_all(repo)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["scan", "--repo", str(repo), "--no-interactive"])
        rendered = output.getvalue()
        self.assertIn("scanned 2 parts", rendered)
        self.assertNotIn("Select a part", rendered)

    # ------------------------------------------------------------------
    # Part grouping and dependency tree
    # ------------------------------------------------------------------

    def test_group_parts_by_language(self):
        parts = [
            {"id": "a.py", "language": "python"},
            {"id": "b.py", "language": "python"},
            {"id": "c.js", "language": "javascript"},
        ]
        groups = group_parts_by_language(parts)
        self.assertEqual(list(groups.keys()), ["python", "javascript"])
        self.assertEqual(len(groups["python"]), 2)
        self.assertEqual(len(groups["javascript"]), 1)

    def test_group_parts_by_directory(self):
        parts = [
            {"id": "src/a.py"},
            {"id": "src/b.py"},
            {"id": "lib/c.py"},
            {"id": "root.py"},
        ]
        groups = group_parts_by_directory(parts)
        self.assertIn("src", groups)
        self.assertIn("lib", groups)
        self.assertIn(".", groups)
        self.assertEqual(len(groups["src"]), 2)
        self.assertEqual(len(groups["."]), 1)

    def test_render_dependency_tree_simple(self):
        parts = [
            {"id": "main.py", "language": "python", "dependencies": ["util.py"], "dependents": []},
            {"id": "util.py", "language": "python", "dependencies": [], "dependents": ["main.py"]},
        ]
        tree = render_dependency_tree(parts)
        self.assertIn("main.py", tree)
        self.assertIn("util.py", tree)
        self.assertIn("python", tree)

    def test_render_dependency_tree_no_edges(self):
        parts = [
            {"id": "a.py", "language": "python", "dependencies": [], "dependents": []},
            {"id": "b.py", "language": "python", "dependencies": [], "dependents": []},
        ]
        tree = render_dependency_tree(parts)
        # Both show up as roots
        self.assertIn("a.py", tree)
        self.assertIn("b.py", tree)

    def test_render_dependency_tree_circular(self):
        parts = [
            {"id": "a.py", "language": "python", "dependencies": ["b.py"], "dependents": ["b.py"]},
            {"id": "b.py", "language": "python", "dependencies": ["a.py"], "dependents": ["a.py"]},
        ]
        tree = render_dependency_tree(parts)
        self.assertIn("circular", tree)

    def test_scan_wizard_groups_shown_interactive(self):
        """When interactive, the wizard should show language/directory groups."""
        repo = self.make_repo()
        (repo / "src").mkdir()
        (repo / "src" / "a.py").write_text("import os\nprint('hello')\n")
        (repo / "src" / "b.py").write_text("import sys\nprint('world')\n")
        (repo / "lib").mkdir()
        (repo / "lib" / "c.js").write_text("console.log('hi');\n")
        self.commit_all(repo)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            # --no-interactive means the grouping wizard is skipped
            main(["scan", "--repo", str(repo), "--no-interactive"])
        rendered = output.getvalue()
        self.assertIn("scanned 3 parts", rendered)
        self.assertNotIn("Which kind", rendered)

    # -----------------------------------------------------------------------
    # Run loop integrity: snapshots, run-scoped metrics, state locking
    # -----------------------------------------------------------------------

    def make_value_repo(self) -> Path:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text("import helper\n\ndef main():\n    return helper.VALUE\n")
        (repo / "value.txt").write_text("10\n")
        self.commit_all(repo)
        main(["scan", "--repo", str(repo), "--no-interactive"])
        return repo

    def value_metric_command(self) -> str:
        script = "print('METRIC=' + open('value.txt').read().strip())"
        return f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"

    def configure_module(self, repo: Path, metric_command: str, *extra: str) -> None:
        main([
            "configure", "--repo", str(repo), "--part", "module.py",
            "--metric", "score", "--metric-command", metric_command,
            "--metric-goal", "minimize", "--no-interactive", *extra,
        ])

    def active_run(self, repo: Path) -> dict:
        state = load_state(repo)
        return state["runs"][state["selection"]["active_run_id"]]

    def evaluate_and_record(self, repo: Path, run_id: str, candidate: str, arm: str | None = None) -> None:
        arm_args = ["--arm", arm] if arm else []
        with contextlib.redirect_stdout(io.StringIO()):
            main(["evaluate", "--repo", str(repo), "--run-id", run_id, "--candidate", candidate, *arm_args])
            main([
                "record", "--repo", str(repo), "--run-id", run_id, "--candidate", candidate,
                "--status", "auto", "--description", candidate, *arm_args,
            ])

    def arm_run(self, repo: Path, parent_id: str, arm_id: str) -> dict:
        state = load_state(repo)
        arm = next(arm for arm in state["runs"][parent_id]["arms"] if arm["arm_id"] == arm_id)
        return state["runs"][arm["child_run_id"]]

    def start_create(
        self, repo: Path, candidates: int = 2, *extra: str, scope: str | None = "value.txt"
    ) -> str:
        scope_args = ["--tune-scope", scope] if scope else []
        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "create", "--repo", str(repo), "--part", "module.py",
                "--feature", "add caching", "--candidates", str(candidates),
                "--metric", "score", "--metric-command", self.value_metric_command(),
                "--metric-goal", "minimize", "--no-interactive", *scope_args, *extra,
            ])
        return self.active_run(repo)["run_id"]

    def test_kept_candidate_edits_carry_into_next_allocation(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(repo, self.value_metric_command(), "--mode", "sequential", "--rounds", "5")
        main(["run", "--repo", str(repo), "--part", "module.py"])
        run_id = self.active_run(repo)["run_id"]
        self.evaluate_and_record(repo, run_id, "seed")

        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        first = get_candidate(self.active_run(repo), "candidate-001")
        # Agent edits without committing.
        (Path(first["worktree_path"]) / "value.txt").write_text("5\n")
        self.evaluate_and_record(repo, run_id, "candidate-001")

        run = self.active_run(repo)
        first = get_candidate(run, "candidate-001")
        self.assertEqual(first["result"]["status"], "keep")
        self.assertEqual(run["current_base_branch"], first["branch"])
        branch_head = subprocess.run(
            ["git", "rev-parse", first["branch"]], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()
        self.assertEqual(first["result"]["commit"], branch_head)
        self.assertNotEqual(branch_head, run["base_ref"])
        self.assertIn(branch_head, Path(run["results_path"]).read_text())

        main(["allocate", "--repo", str(repo), "--run-id", run_id])
        second = get_candidate(self.active_run(repo), "candidate-002")
        self.assertEqual((Path(second["worktree_path"]) / "value.txt").read_text(), "5\n")

    def test_record_rejects_commits_made_after_evaluate(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(repo, self.value_metric_command(), "--mode", "sequential", "--rounds", "5")
        main(["run", "--repo", str(repo), "--part", "module.py"])
        run = self.active_run(repo)
        seed_path = Path(run["candidates"][0]["worktree_path"])
        with contextlib.redirect_stdout(io.StringIO()):
            main(["evaluate", "--repo", str(repo), "--run-id", run["run_id"], "--candidate", "seed"])
        (seed_path / "value.txt").write_text("1\n")
        self.commit_all(seed_path, "sneaky edit")

        with self.assertRaises(SystemExit) as exc:
            main([
                "record", "--repo", str(repo), "--run-id", run["run_id"], "--candidate", "seed",
                "--status", "auto", "--description", "baseline",
            ])
        self.assertIn("re-run evaluate", str(exc.exception))

    def test_delete_run_evaluates_with_its_own_metric(self) -> None:
        repo = self.make_value_repo()
        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "delete", "--repo", str(repo), "--part", "helper.py",
                "--metric", "score", "--metric-command", self.value_metric_command(),
                "--metric-goal", "minimize", "--no-interactive",
            ])
        parent_id = self.active_run(repo)["run_id"]
        self.assertNotIn("helper.py", load_state(repo).get("part_configs", {}))

        with contextlib.redirect_stdout(io.StringIO()):
            main(["arm-ready", "--repo", str(repo), "--run-id", parent_id, "--arm", "deleted"])
        self.evaluate_and_record(repo, parent_id, "seed", arm="deleted")
        child = self.arm_run(repo, parent_id, "deleted")
        seed = get_candidate(child, "seed")
        self.assertEqual(seed["result"]["metric_value"], 10.0)
        self.assertEqual(seed["result"]["status"], "keep")

        # The deletion is committed on the arm's seed branch, so candidates inherit it.
        with contextlib.redirect_stdout(io.StringIO()):
            main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", "deleted"])
        candidate = get_candidate(self.arm_run(repo, parent_id, "deleted"), "candidate-001")
        self.assertFalse((Path(candidate["worktree_path"]) / "helper.py").exists())

    def test_create_keeps_existing_part_config_and_uses_run_metric(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(
            repo, "python -c \"print('METRIC=1.0')\"", "--mode", "sequential", "--rounds", "2"
        )
        before = load_state(repo)["part_configs"]["module.py"]

        parent_id = self.start_create(repo, candidates=2)
        self.assertEqual(load_state(repo)["part_configs"]["module.py"], before)

        self.evaluate_and_record(repo, parent_id, "seed", arm="control")
        seed = get_candidate(self.arm_run(repo, parent_id, "control"), "seed")
        self.assertEqual(seed["result"]["metric_value"], 10.0)

    def test_concurrent_evaluate_and_record_do_not_lose_updates(self) -> None:
        repo = self.make_value_repo()
        script = "import time; time.sleep(0.5); print('METRIC=' + open('value.txt').read().strip())"
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"
        self.configure_module(
            repo, command, "--mode", "parallel", "--parallelism", "4", "--rounds", "10"
        )
        with contextlib.redirect_stdout(io.StringIO()):
            main(["run", "--repo", str(repo), "--part", "module.py"])
        run = self.active_run(repo)
        candidate_ids = [c["candidate_id"] for c in run["candidates"] if c["candidate_id"] != "seed"]
        self.assertEqual(len(candidate_ids), 4)
        for index, candidate_id in enumerate(candidate_ids):
            path = Path(get_candidate(run, candidate_id)["worktree_path"])
            (path / "value.txt").write_text(f"{index + 1}\n")

        cli = [sys.executable, str(REPO_ROOT / "scripts" / "autoresearch_wrapper.py")]

        def run_all(build_args) -> None:
            procs = [
                subprocess.Popen(
                    cli + build_args(candidate_id),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for candidate_id in candidate_ids
            ]
            for proc in procs:
                _, stderr = proc.communicate(timeout=120)
                self.assertEqual(proc.returncode, 0, stderr)

        run_all(lambda cid: [
            "evaluate", "--repo", str(repo), "--run-id", run["run_id"], "--candidate", cid,
        ])
        run_all(lambda cid: [
            "record", "--repo", str(repo), "--run-id", run["run_id"], "--candidate", cid,
            "--status", "auto", "--description", cid,
        ])

        run = self.active_run(repo)
        for candidate_id in candidate_ids:
            candidate = get_candidate(run, candidate_id)
            self.assertIn("latest_evaluation", candidate, candidate_id)
            self.assertIn("result", candidate, candidate_id)
        self.assertEqual(run["rounds_completed"], 4)
        self.assertEqual(run["best_metric"], 1.0)
        rows = Path(run["results_path"]).read_text().strip().splitlines()
        self.assertEqual(len(rows), 1 + 4)

    def start_value_run(self, repo: Path, *extra: str) -> str:
        self.configure_module(
            repo, self.value_metric_command(), "--mode", "sequential", "--rounds", "5", *extra
        )
        with contextlib.redirect_stdout(io.StringIO()):
            main(["run", "--repo", str(repo), "--part", "module.py"])
        return self.active_run(repo)["run_id"]

    def allocate_with_value(self, repo: Path, run_id: str, value: str) -> str:
        with contextlib.redirect_stdout(io.StringIO()):
            main(["allocate", "--repo", str(repo), "--run-id", run_id])
        candidate = self.active_run(repo)["candidates"][-1]
        (Path(candidate["worktree_path"]) / "value.txt").write_text(f"{value}\n")
        return candidate["candidate_id"]

    def test_run_does_not_resume_create_run_for_same_part(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(repo, self.value_metric_command(), "--mode", "sequential", "--rounds", "2")
        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "create", "--repo", str(repo), "--part", "module.py",
                "--feature", "add caching", "--candidates", "2",
                "--metric", "score", "--metric-command", self.value_metric_command(),
                "--metric-goal", "minimize", "--no-interactive",
            ])
        create_run_id = self.active_run(repo)["run_id"]
        time.sleep(1.1)  # run ids have one-second resolution

        with contextlib.redirect_stdout(io.StringIO()):
            main(["run", "--repo", str(repo), "--part", "module.py"])
        run = self.active_run(repo)
        self.assertNotEqual(run["run_id"], create_run_id)
        self.assertEqual(run["run_type"], "optimize")

    def test_metric_timeout_kills_command_and_auto_records_crash(self) -> None:
        repo = self.make_value_repo()
        command = f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(60)'"
        self.configure_module(
            repo, command, "--mode", "sequential", "--rounds", "5", "--metric-timeout", "1"
        )
        # Re-configuring without the flag keeps the timeout.
        self.configure_module(repo, command)
        self.assertEqual(load_state(repo)["part_configs"]["module.py"]["metric"]["timeout"], 1.0)
        with contextlib.redirect_stdout(io.StringIO()):
            main(["run", "--repo", str(repo), "--part", "module.py"])
        run_id = self.active_run(repo)["run_id"]

        started = time.monotonic()
        self.evaluate_and_record(repo, run_id, "seed")
        self.assertLess(time.monotonic() - started, 20)

        seed = get_candidate(self.active_run(repo), "seed")
        self.assertTrue(seed["latest_evaluation"]["timed_out"])
        self.assertEqual(seed["result"]["status"], "crash")

    def test_record_rejects_second_record_of_same_candidate(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo)
        self.evaluate_and_record(repo, run_id, "seed")
        with self.assertRaises(SystemExit) as exc:
            main([
                "record", "--repo", str(repo), "--run-id", run_id, "--candidate", "seed",
                "--status", "auto",
            ])
        self.assertIn("already recorded", str(exc.exception))
        rows = Path(self.active_run(repo)["results_path"]).read_text().strip().splitlines()
        self.assertEqual(len(rows), 2)

    def test_manual_keep_of_worse_metric_preserves_best(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo)
        self.evaluate_and_record(repo, run_id, "seed")
        candidate_id = self.allocate_with_value(repo, run_id, "20")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["evaluate", "--repo", str(repo), "--run-id", run_id, "--candidate", candidate_id])
            main([
                "record", "--repo", str(repo), "--run-id", run_id, "--candidate", candidate_id,
                "--status", "keep", "--description", "keep for readability",
            ])
        run = self.active_run(repo)
        self.assertEqual(run["best_metric"], 10.0)
        self.assertEqual(run["best_candidate_id"], "seed")
        self.assertEqual(run["current_base_branch"], get_candidate(run, candidate_id)["branch"])

    def test_crashes_count_toward_early_exit(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo, "--early-exit-patience", "2")
        self.evaluate_and_record(repo, run_id, "seed")
        # Allocate everything up front, as parallel workers would.
        crashes = [self.allocate_with_value(repo, run_id, "not-a-number") for _ in range(2)]
        straggler = self.allocate_with_value(repo, run_id, "1")
        for candidate_id in crashes:
            self.evaluate_and_record(repo, run_id, candidate_id)
        run = self.active_run(repo)
        self.assertEqual(run["status"], "early_exit")
        self.assertEqual(run["early_exit"]["rounds_without_improvement"], 2)

        # A straggler recorded after the run ended must not reopen it.
        self.evaluate_and_record(repo, run_id, straggler)
        self.assertEqual(self.active_run(repo)["status"], "early_exit")

    def test_parse_metric_value_uses_last_match(self) -> None:
        output = "METRIC=9.0\nepoch 2\nMETRIC=3.5\n"
        self.assertEqual(parse_metric_value(output, DEFAULT_METRIC_REGEX), 3.5)

    # -----------------------------------------------------------------------
    # Stop rules
    # -----------------------------------------------------------------------

    def run_candidates(self, repo: Path, run_id: str, values: list[str]) -> None:
        for value in values:
            candidate_id = self.allocate_with_value(repo, run_id, value)
            self.evaluate_and_record(repo, run_id, candidate_id)

    def test_configure_rejects_unparseable_stop_rule(self) -> None:
        repo = self.make_value_repo()
        with self.assertRaises(SystemExit) as exc:
            self.configure_module(
                repo, self.value_metric_command(), "--mode", "sequential", "--stop-rule", "until it is good"
            )
        self.assertIn("invalid stop rule", str(exc.exception))

    def test_metric_threshold_stop_rule_completes_run_and_blocks_allocate(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo, "--rounds", "10", "--stop-rule", "metric<=5")
        self.evaluate_and_record(repo, run_id, "seed")
        self.run_candidates(repo, run_id, ["8"])
        self.assertEqual(self.active_run(repo)["status"], "running")
        self.run_candidates(repo, run_id, ["4"])

        run = self.active_run(repo)
        self.assertEqual(run["status"], "completed")
        self.assertIn("<= 5", run["stop_reason"])
        with self.assertRaises(SystemExit) as exc:
            main(["allocate", "--repo", str(repo), "--run-id", run_id])
        self.assertIn("is completed", str(exc.exception))

    def test_stalled_stop_rule_counts_consecutive_non_improvements(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo, "--rounds", "10", "--stop-rule", "stalled:2, metric<=0")
        self.evaluate_and_record(repo, run_id, "seed")
        self.run_candidates(repo, run_id, ["12", "9", "11"])
        self.assertEqual(self.active_run(repo)["status"], "running")
        self.run_candidates(repo, run_id, ["not-a-number"])

        run = self.active_run(repo)
        self.assertEqual(run["status"], "completed")
        self.assertIn("2 rounds without improvement", run["stop_reason"])

    def test_stop_rule_alone_satisfies_run_gate_and_minutes_rule_stops_allocate(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(
            repo, self.value_metric_command(), "--mode", "sequential", "--stop-rule", "minutes:0"
        )
        self.assertIsNone(load_state(repo)["part_configs"]["module.py"]["execution"]["rounds"])
        with contextlib.redirect_stdout(io.StringIO()):
            main(["run", "--repo", str(repo), "--part", "module.py"])
        run_id = self.active_run(repo)["run_id"]

        with self.assertRaises(SystemExit) as exc:
            main(["allocate", "--repo", str(repo), "--run-id", run_id])
        self.assertIn("minutes elapsed", str(exc.exception))
        self.assertEqual(self.active_run(repo)["status"], "completed")

    def test_legacy_free_text_stop_rule_does_not_replace_rounds(self) -> None:
        repo = self.make_value_repo()
        self.configure_module(repo, self.value_metric_command(), "--mode", "sequential", "--rounds", "3")
        state = load_state(repo)
        execution = state["part_configs"]["module.py"]["execution"]
        execution["rounds"] = None
        execution["stop_rule"] = "until latency looks good"
        write_state(repo, state)

        with self.assertRaises(SystemExit) as exc:
            main(["run", "--repo", str(repo), "--part", "module.py"])
        self.assertIn("execution.rounds_or_stop_rule", str(exc.exception))

    # -----------------------------------------------------------------------
    # Finalize
    # -----------------------------------------------------------------------

    def git_out(self, cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()

    def finished_run_with_improvement(self, repo: Path) -> str:
        run_id = self.start_value_run(repo, "--rounds", "2")
        self.evaluate_and_record(repo, run_id, "seed")
        self.run_candidates(repo, run_id, ["5", "7"])
        self.assertEqual(self.active_run(repo)["status"], "completed")
        return run_id

    def finalize(self, repo: Path, run_id: str, *flags: str) -> dict:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["finalize", "--repo", str(repo), "--run-id", run_id, "--json", *flags])
        return json.loads(buffer.getvalue())

    def test_finalize_merges_best_stages_it_and_cleans_up(self) -> None:
        repo = self.make_value_repo()
        run_id = self.finished_run_with_improvement(repo)
        run = self.active_run(repo)
        best = get_candidate(run, run["best_candidate_id"])
        self.assertEqual(best["candidate_id"], "candidate-001")

        payload = self.finalize(repo, run_id, "--merge", "--prune-branches")

        self.assertTrue(payload["merged"])
        self.assertEqual((repo / "value.txt").read_text(), "5\n")
        self.assertEqual(self.git_out(repo, "diff", "--cached", "--name-only"), "value.txt")
        self.assertEqual(self.git_out(repo, "log", "-1", "--format=%s"), "init")  # staged, not committed
        run = self.active_run(repo)
        for candidate in run["candidates"]:
            self.assertFalse(Path(candidate["worktree_path"]).exists(), candidate["candidate_id"])
            self.assertTrue(candidate["missing"])
        self.assertFalse(Path(run["worktree_root"]).exists())
        remaining = self.git_out(repo, "branch", "--list", "autoresearch/*", "--format=%(refname:short)")
        self.assertEqual(remaining.splitlines(), [best["branch"]])
        self.assertEqual(run["finalized"]["skipped"], [])

    def test_finalize_without_merge_keeps_branches_and_suggests_commands(self) -> None:
        repo = self.make_value_repo()
        run_id = self.finished_run_with_improvement(repo)
        payload = self.finalize(repo, run_id)
        self.assertFalse(payload["merged"])
        self.assertTrue(any("git merge --squash" in step for step in payload["next_steps"]))
        self.assertEqual((repo / "value.txt").read_text(), "10\n")
        branches = self.git_out(repo, "branch", "--list", "autoresearch/*").splitlines()
        self.assertEqual(len(branches), 3)  # seed + 2 candidates

    def test_finalize_refuses_running_run_unless_stopped(self) -> None:
        repo = self.make_value_repo()
        run_id = self.start_value_run(repo)
        with self.assertRaises(SystemExit) as exc:
            self.finalize(repo, run_id)
        self.assertIn("--stop", str(exc.exception))
        payload = self.finalize(repo, run_id, "--stop")
        self.assertEqual(payload["status"], "completed")
        self.assertFalse(payload["best_has_changes"])

    def test_finalize_merge_refuses_dirty_checkout_and_leaves_worktrees(self) -> None:
        repo = self.make_value_repo()
        run_id = self.finished_run_with_improvement(repo)
        (repo / "module.py").write_text("# local edit\n")
        with self.assertRaises(SystemExit) as exc:
            self.finalize(repo, run_id, "--merge")
        self.assertIn("uncommitted changes", str(exc.exception))
        for candidate in self.active_run(repo)["candidates"]:
            self.assertTrue(Path(candidate["worktree_path"]).exists())

    def test_finalize_skips_dirty_worktree_unless_forced(self) -> None:
        repo = self.make_value_repo()
        run_id = self.finished_run_with_improvement(repo)
        dirty = get_candidate(self.active_run(repo), "candidate-002")
        (Path(dirty["worktree_path"]) / "scratch.log").write_text("metric output\n")

        payload = self.finalize(repo, run_id)
        self.assertEqual([item["item"] for item in payload["skipped"]], ["candidate-002"])
        self.assertTrue(Path(dirty["worktree_path"]).exists())

        payload = self.finalize(repo, run_id, "--force")
        self.assertEqual(payload["removed_worktrees"], ["candidate-002"])
        self.assertFalse(Path(dirty["worktree_path"]).exists())

    # -----------------------------------------------------------------------
    # Comparison runs (create / delete arms)
    # -----------------------------------------------------------------------

    def setup_arm(self, repo: Path, parent_id: str, arm_id: str, value: str) -> None:
        state = load_state(repo)
        arm = next(arm for arm in state["runs"][parent_id]["arms"] if arm["arm_id"] == arm_id)
        (Path(arm["setup"]["worktree_path"]) / "value.txt").write_text(f"{value}\n")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["arm-ready", "--repo", str(repo), "--run-id", parent_id, "--arm", arm_id])

    def tune_arm(self, repo: Path, parent_id: str, arm_id: str, values: list[str]) -> None:
        self.evaluate_and_record(repo, parent_id, "seed", arm=arm_id)
        for value in values:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", arm_id])
            candidate = self.arm_run(repo, parent_id, arm_id)["candidates"][-1]
            (Path(candidate["worktree_path"]) / "value.txt").write_text(f"{value}\n")
            self.evaluate_and_record(repo, parent_id, candidate["candidate_id"], arm=arm_id)

    def compare(self, repo: Path, parent_id: str) -> dict:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["compare", "--repo", str(repo), "--run-id", parent_id, "--json"])
        return json.loads(buffer.getvalue())

    def test_create_readies_control_and_keeps_approaches_in_setup(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 2)
        parent = self.active_run(repo)
        phases = {arm["arm_id"]: arm["phase"] for arm in parent["arms"]}
        self.assertEqual(phases, {"control": "tuning", "approach-A": "setup", "approach-B": "setup"})
        control = self.arm_run(repo, parent_id, "control")
        self.assertEqual(control["parent_run_id"], parent_id)
        self.assertEqual(control["base_ref"], parent["base_ref"])

        with self.assertRaises(SystemExit) as exc:
            main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", "approach-A"])
        self.assertIn("still in setup", str(exc.exception))
        with self.assertRaises(SystemExit) as exc:
            main(["allocate", "--repo", str(repo), "--run-id", parent_id])
        self.assertIn("pass --arm", str(exc.exception))
        with self.assertRaises(SystemExit) as exc:
            main(["finalize", "--repo", str(repo), "--run-id", control["run_id"]])
        self.assertIn("finalize that run instead", str(exc.exception))

    def test_arm_ready_starts_child_from_setup_commit_with_equal_budget(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "4", "--stop-rule", "stalled:2")
        self.setup_arm(repo, parent_id, "approach-A", "7")

        parent = self.active_run(repo)
        arm = next(arm for arm in parent["arms"] if arm["arm_id"] == "approach-A")
        child = self.arm_run(repo, parent_id, "approach-A")
        self.assertEqual(arm["phase"], "tuning")
        self.assertEqual(child["base_ref"], arm["setup_commit"])
        self.assertNotEqual(arm["setup_commit"], parent["base_ref"])
        self.assertEqual(self.git_out(repo, "rev-parse", child["candidates"][0]["branch"]), arm["setup_commit"])
        control = self.arm_run(repo, parent_id, "control")
        for run in (child, control):
            self.assertEqual(run["execution"]["rounds"], 4)
            self.assertEqual(run["execution"]["stop_rule"], "stalled:2")
        self.assertTrue(Path(child["program_path"]).exists())

        self.evaluate_and_record(repo, parent_id, "seed", arm="approach-A")
        seed = get_candidate(self.arm_run(repo, parent_id, "approach-A"), "seed")
        self.assertEqual(seed["result"]["metric_value"], 7.0)

        with self.assertRaises(SystemExit) as exc:
            main(["arm-ready", "--repo", str(repo), "--run-id", parent_id, "--arm", "approach-A"])
        self.assertIn("already tuning", str(exc.exception))

    def test_create_comparison_picks_tuned_winner_and_finalize_merges_it(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 2, "--rounds", "1")
        self.setup_arm(repo, parent_id, "approach-A", "6")
        self.setup_arm(repo, parent_id, "approach-B", "8")
        self.tune_arm(repo, parent_id, "control", ["9"])
        self.assertEqual(self.active_run(repo)["status"], "running")
        self.tune_arm(repo, parent_id, "approach-A", ["5"])
        self.tune_arm(repo, parent_id, "approach-B", ["12"])
        self.assertEqual(self.active_run(repo)["status"], "completed")

        result = self.compare(repo, parent_id)
        rows = {row["arm_id"]: row for row in result["arms"]}
        self.assertEqual(result["winner_arm"], "approach-A")
        self.assertEqual(result["incomplete_arms"], [])
        self.assertEqual(rows["control"]["setup_metric"], 10.0)
        self.assertEqual(rows["control"]["best_metric"], 9.0)
        self.assertEqual(rows["approach-A"]["setup_metric"], 6.0)
        self.assertEqual(rows["approach-A"]["tuning_gain"], -1.0)
        self.assertEqual(rows["approach-A"]["delta_vs_control"], -4.0)
        self.assertEqual(rows["approach-B"]["best_metric"], 8.0)

        payload = self.finalize(repo, parent_id, "--merge", "--prune-branches")
        self.assertEqual(payload["winner_arm"], "approach-A")
        self.assertTrue(payload["merged"])
        self.assertEqual((repo / "value.txt").read_text(), "5\n")
        state = load_state(repo)
        parent = state["runs"][parent_id]
        for arm in parent["arms"]:
            for candidate in state["runs"][arm["child_run_id"]]["candidates"]:
                self.assertFalse(Path(candidate["worktree_path"]).exists())
        self.assertFalse(Path(parent["worktree_root"]).exists())
        remaining = self.git_out(repo, "branch", "--list", "autoresearch/*", "--format=%(refname:short)")
        self.assertEqual(remaining.splitlines(), [payload["best_branch"]])

    def test_tie_goes_to_control_and_text_compare_renders(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "1")
        self.setup_arm(repo, parent_id, "approach-A", "9")
        self.tune_arm(repo, parent_id, "control", ["9"])
        self.tune_arm(repo, parent_id, "approach-A", ["9"])
        self.assertEqual(self.compare(repo, parent_id)["winner_arm"], "control")

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["compare", "--repo", str(repo), "--run-id", parent_id])
        self.assertIn("| control * |", buffer.getvalue())

    def test_compare_flags_incomplete_arms_and_finalize_needs_stop(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "2")
        self.tune_arm(repo, parent_id, "control", ["9"])
        result = self.compare(repo, parent_id)
        self.assertEqual(result["incomplete_arms"], ["control", "approach-A"])
        self.assertEqual(result["winner_arm"], "control")

        with self.assertRaises(SystemExit) as exc:
            self.finalize(repo, parent_id)
        self.assertIn("--stop", str(exc.exception))
        payload = self.finalize(repo, parent_id, "--stop")
        parent = load_state(repo)["runs"][parent_id]
        phases = {arm["arm_id"]: arm["phase"] for arm in parent["arms"]}
        self.assertEqual(phases, {"control": "done", "approach-A": "abandoned"})
        self.assertIn("approach-A/seed", payload["removed_worktrees"])
        self.assertFalse(Path(parent["worktree_root"]).exists())

    def test_delete_comparison_uses_control_as_pre_deletion_baseline(self) -> None:
        repo = self.make_value_repo()
        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "delete", "--repo", str(repo), "--part", "helper.py", "--rounds", "1",
                "--tune-scope", "value.txt",
                "--metric", "score", "--metric-command", self.value_metric_command(),
                "--metric-goal", "minimize", "--no-interactive",
            ])
        parent_id = self.active_run(repo)["run_id"]
        self.setup_arm(repo, parent_id, "deleted", "10")
        self.tune_arm(repo, parent_id, "control", ["10"])
        self.tune_arm(repo, parent_id, "deleted", ["4"])

        result = self.compare(repo, parent_id)
        rows = {row["arm_id"]: row for row in result["arms"]}
        self.assertEqual(rows["control"]["setup_metric"], 10.0)
        self.assertEqual(result["winner_arm"], "deleted")
        self.assertEqual(rows["deleted"]["delta_vs_control"], -6.0)

    # -----------------------------------------------------------------------
    # Tuning scope enforcement
    # -----------------------------------------------------------------------

    def test_default_tune_scopes(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, scope=None)
        self.assertEqual(load_state(repo)["runs"][parent_id]["tune_scope"], ["helper.py", "module.py"])
        self.assertEqual(self.arm_run(repo, parent_id, "control")["tune_scope"], ["helper.py", "module.py"])
        self.assertIn("Tuning scope (enforced)", Path(self.arm_run(repo, parent_id, "control")["program_path"]).read_text())

        with contextlib.redirect_stdout(io.StringIO()):
            main([
                "delete", "--repo", str(repo), "--part", "helper.py",
                "--metric", "score", "--metric-command", self.value_metric_command(),
                "--metric-goal", "minimize", "--no-interactive",
            ])
        self.assertEqual(self.active_run(repo)["tune_scope"], ["module.py"])

    def test_tune_scope_marks_directories(self) -> None:
        repo = self.make_value_repo()
        (repo / "src").mkdir()
        (repo / "src" / "x.py").write_text("X = 1\n")
        self.commit_all(repo, "add src")
        parent_id = self.start_create(repo, 1, scope="src, value.txt,./module.py")
        self.assertEqual(
            load_state(repo)["runs"][parent_id]["tune_scope"], ["module.py", "src/", "value.txt"]
        )
        with self.assertRaises(SystemExit):
            self.start_create(repo, 1, scope="../outside.py")

    def test_evaluate_rejects_out_of_scope_edit_before_running_metric(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "3", scope=None)
        self.evaluate_and_record(repo, parent_id, "seed", arm="control")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", "control"])
        candidate = self.arm_run(repo, parent_id, "control")["candidates"][-1]
        (Path(candidate["worktree_path"]) / "value.txt").write_text("1\n")

        evaluate = [
            "evaluate", "--repo", str(repo), "--run-id", parent_id, "--arm", "control",
            "--candidate", candidate["candidate_id"],
        ]
        with self.assertRaises(SystemExit) as exc:
            main(evaluate)
        self.assertIn("outside the arm's tuning scope: value.txt", str(exc.exception))
        rejected = get_candidate(self.arm_run(repo, parent_id, "control"), candidate["candidate_id"])
        self.assertNotIn("latest_evaluation", rejected)

        with contextlib.redirect_stdout(io.StringIO()):
            main([*evaluate, "--allow-out-of-scope"])
            # Accepted at evaluate, so record needs no second flag.
            main([
                "record", "--repo", str(repo), "--run-id", parent_id, "--arm", "control",
                "--candidate", candidate["candidate_id"], "--status", "auto",
            ])
        recorded = get_candidate(self.arm_run(repo, parent_id, "control"), candidate["candidate_id"])
        self.assertEqual(recorded["result"]["out_of_scope"], ["value.txt"])
        rows = {row["arm_id"]: row for row in self.compare(repo, parent_id)["arms"]}
        self.assertEqual(rows["control"]["out_of_scope_candidates"], [candidate["candidate_id"]])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["compare", "--repo", str(repo), "--run-id", parent_id])
        self.assertIn("Out-of-scope edits accepted", buffer.getvalue())

    def test_files_changed_in_setup_join_that_arms_scope_only(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "3", scope="module.py")
        arm = next(a for a in self.active_run(repo)["arms"] if a["arm_id"] == "approach-A")
        (Path(arm["setup"]["worktree_path"]) / "cache.py").write_text("SIZE = 8\n")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["arm-ready", "--repo", str(repo), "--run-id", parent_id, "--arm", "approach-A"])
        self.assertEqual(self.arm_run(repo, parent_id, "approach-A")["tune_scope"], ["cache.py", "module.py"])
        self.assertEqual(self.arm_run(repo, parent_id, "control")["tune_scope"], ["module.py"])

        self.evaluate_and_record(repo, parent_id, "seed", arm="approach-A")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", "approach-A"])
        candidate = self.arm_run(repo, parent_id, "approach-A")["candidates"][-1]
        (Path(candidate["worktree_path"]) / "cache.py").write_text("SIZE = 64\n")
        self.evaluate_and_record(repo, parent_id, candidate["candidate_id"], arm="approach-A")
        recorded = get_candidate(self.arm_run(repo, parent_id, "approach-A"), candidate["candidate_id"])
        self.assertNotIn("out_of_scope", recorded["result"])

    def test_record_backstop_rejects_manual_out_of_scope_value(self) -> None:
        repo = self.make_value_repo()
        parent_id = self.start_create(repo, 1, "--rounds", "3", scope="module.py")
        self.evaluate_and_record(repo, parent_id, "seed", arm="control")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["allocate", "--repo", str(repo), "--run-id", parent_id, "--arm", "control"])
        candidate = self.arm_run(repo, parent_id, "control")["candidates"][-1]
        (Path(candidate["worktree_path"]) / "helper.py").write_text("VALUE = 2\n")
        record = [
            "record", "--repo", str(repo), "--run-id", parent_id, "--arm", "control",
            "--candidate", candidate["candidate_id"], "--metric-value", "3", "--status", "auto",
        ]
        with self.assertRaises(SystemExit) as exc:
            main(record)
        self.assertIn("helper.py", str(exc.exception))
        with contextlib.redirect_stdout(io.StringIO()):
            main([*record, "--allow-out-of-scope"])
        recorded = get_candidate(self.arm_run(repo, parent_id, "control"), candidate["candidate_id"])
        self.assertEqual(recorded["result"]["out_of_scope"], ["helper.py"])

    def test_compare_refuses_legacy_create_run(self) -> None:
        repo = self.make_value_repo()
        state = load_state(repo)
        state.setdefault("runs", {})["legacy"] = {
            "run_id": "legacy", "part_id": "module.py", "run_type": "create",
            "status": "running", "candidates": [],
            "results_path": str(state_dir(repo) / "runs" / "legacy" / "results.tsv"),
        }
        write_state(repo, state)
        with self.assertRaises(SystemExit) as exc:
            main(["compare", "--repo", str(repo), "--run-id", "legacy"])
        self.assertIn("legacy create run", str(exc.exception))

    def test_affected_parts_are_direct_neighbours_only(self) -> None:
        repo = self.make_repo()
        (repo / "a.py").write_text("def a(): pass\n")
        (repo / "b.py").write_text("import a\ndef b(): pass\n")
        (repo / "c.py").write_text("import b\ndef c(): pass\n")
        self.commit_all(repo)
        main(["scan", "--repo", str(repo), "--no-interactive"])
        state = load_state(repo)
        self.assertEqual(identify_affected_parts(state, ["a.py"]), ["b.py"])
        self.assertEqual(identify_affected_parts(state, ["b.py"]), ["a.py", "c.py"])

    def test_mkdir_lock_times_out_and_reclaims_stale_lock(self) -> None:
        lock_dir = Path(tempfile.mkdtemp(prefix="autoresearch-lock-")) / "state.lock.d"
        lock_dir.mkdir()
        with self.assertRaises(SystemExit):
            with mkdir_lock(lock_dir, timeout=0.2, stale_after=60):
                pass
        old = time.time() - 120
        os.utime(lock_dir, (old, old))
        with mkdir_lock(lock_dir, timeout=1.0, stale_after=60):
            self.assertTrue(lock_dir.exists())
        self.assertFalse(lock_dir.exists())


if __name__ == "__main__":
    unittest.main()
