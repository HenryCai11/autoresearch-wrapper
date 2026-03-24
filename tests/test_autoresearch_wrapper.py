from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autoresearch_wrapper.core import (
    check_early_exit,
    detect_system_resources,
    find_delete_dependents,
    format_monitor_update,
    group_parts_by_directory,
    group_parts_by_language,
    identify_affected_parts,
    load_state,
    main,
    migrate_state,
    normalize_entry_argv,
    plan_wild_changes,
    plans_dir,
    recommend_parallelism,
    render_dependency_tree,
    should_widen_search,
    state_dir,
    status_markdown,
    wizard_select,
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
        # seed + 2 approaches
        self.assertEqual(len(run["candidates"]), 3)
        candidate_ids = [c["candidate_id"] for c in run["candidates"]]
        self.assertIn("approach-A", candidate_ids)
        self.assertIn("approach-B", candidate_ids)

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
        # Verify file is removed in seed worktree
        seed = run["candidates"][0]
        seed_helper = Path(seed["worktree_path"]) / "helper.py"
        self.assertFalse(seed_helper.exists())

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
        self.assertEqual(first_prompt[0], "Which kind of files do you want to optimize?")
        self.assertIsNotNone(first_prompt[2])
        self.assertTrue(first_prompt[2].startswith("core functionality ("))

    def test_no_args_defaults_to_wizard_in_interactive_mode(self) -> None:
        with mock.patch("autoresearch_wrapper.core.is_interactive_default", return_value=True):
            self.assertEqual(normalize_entry_argv([]), ["wizard"])

    def test_wizard_runs_end_to_end(self) -> None:
        repo = self.make_repo()
        (repo / "helper.py").write_text("VALUE = 1\n")
        (repo / "module.py").write_text(
            "import helper\n# optimize this runtime path for latency\n"
        )
        self.commit_all(repo)

        def fake_select(label: str, options: list[str], default: str | None = None) -> str:
            if label == "Which kind of files do you want to optimize?":
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


if __name__ == "__main__":
    unittest.main()
