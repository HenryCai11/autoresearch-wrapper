from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autoresearch_wrapper.core import load_state, main, plans_dir, state_dir, status_markdown


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


if __name__ == "__main__":
    unittest.main()
