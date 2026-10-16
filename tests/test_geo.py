from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autoresearch_wrapper.geo import apply_operations, build_graph, compare_platforms, prioritize, readiness


class GeoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "index.html").write_text(
            '<html><head><title>EAU research project</title>'
            '<meta name="description" content="Environment agent user co-evolution">'
            '<link rel="canonical" href="https://example.org/">'
            '<script type="application/ld+json">{"url":"https://example.org/",'
            '"sameAs":"https://arxiv.org/abs/1234.56789"}</script></head>'
            '<body><section id="one">First</section>'
            '<section id="two">Second</section>'
            '<a href="https://arxiv.org/abs/1234.56789">paper</a></body></html>',
            encoding="utf-8",
        )
        (self.repo / "README.md").write_text("Project page coming soon", encoding="utf-8")
        (self.repo / "robots.txt").write_text("User-agent: *\nAllow: /", encoding="utf-8")
        (self.repo / "sitemap.xml").write_text("https://example.org/", encoding="utf-8")
        self.config = {"site_url": "https://example.org/", "paper_url": "https://arxiv.org/abs/1234.56789",
                       "platforms": {"Doubao": 0.4, "DeepSeek": 0.6}, "queries": ["recent agent co-evolution"]}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_graph_exposes_internal_sections_and_outcomes(self) -> None:
        graph = build_graph(self.repo, self.config)
        ids = {node["id"] for node in graph["nodes"]}
        self.assertIn("section:one", ids)
        self.assertIn("meta:canonical", ids)
        self.assertIn("outcome:Doubao:retrieval", ids)
        self.assertIn("outcome:DeepSeek:answer", ids)
        self.assertIn({"from": "file:index.html", "to": "section:one", "kind": "contains"}, graph["edges"])

    def test_prioritization_uses_returned_urls_not_graph_reachability(self) -> None:
        self.config["repo_url"] = "https://github.com/example/repo"
        self.config["interventions"] = [
            {"id": "readme", "nodes": ["file:README.md"], "source_url": self.config["repo_url"],
             "cost": .1, "current_gap": True},
            {"id": "paper-link", "nodes": ["external:paper-backlink"],
             "source_url": self.config["paper_url"], "cost": 100, "current_gap": False},
        ]
        evidence = {"tool": "GPT/Codex web search", "observations": [
            {"query_id": "Q1", "result_urls": [self.config["paper_url"]]},
            {"query_id": "Q2", "result_urls": [self.config["paper_url"]]},
        ]}
        result = prioritize(self.config, evidence)
        self.assertEqual(result["observed_funnel"],
                         {"project_returned": 0, "paper_returned": 2, "repo_returned": 0})
        self.assertEqual(result["interventions"][0]["id"], "paper-link")
        self.assertEqual(result["interventions"][0]["observed_opportunity_count"], 2)
        self.assertIsNone(result["interventions"][1]["next_test_order"])
        self.assertNotIn("reachable_outcomes", result["interventions"][0])
        self.assertNotIn("structural_priority", result["interventions"][0])

    def test_graph_tracks_node_content_when_topology_is_unchanged(self) -> None:
        before = build_graph(self.repo, self.config)
        before_nodes = {node["id"]: node for node in before["nodes"]}
        (self.repo / "README.md").write_text("A clearer project summary", encoding="utf-8")
        after = build_graph(self.repo, self.config)
        after_nodes = {node["id"]: node for node in after["nodes"]}
        self.assertEqual(before["edges"], after["edges"])
        self.assertNotEqual(before_nodes["file:README.md"]["content_sha256"],
                            after_nodes["file:README.md"]["content_sha256"])
        self.assertEqual(before_nodes["file:index.html"]["content_sha256"],
                         after_nodes["file:index.html"]["content_sha256"])

    def test_scoped_add_edit_move_and_local_score(self) -> None:
        before = readiness(self.repo, self.config)["score"]
        dry = apply_operations(self.repo, self.config, [
            {"op": "move_after", "node": "section:one", "after_node": "section:two"},
            {"op": "add_after", "node": "section:two", "html": '<section id="three">New</section>'},
            {"op": "replace_text", "node": "file:README.md", "before": "Project page coming soon",
             "after": "https://example.org/ explains co-evolution"},
        ])
        self.assertFalse(dry["applied"])
        self.assertEqual(readiness(self.repo, self.config)["score"], before)
        applied = apply_operations(self.repo, self.config, [
            {"op": "move_after", "node": "section:one", "after_node": "section:two"},
            {"op": "replace_text", "node": "file:README.md", "before": "Project page coming soon",
             "after": "https://example.org/ explains co-evolution"},
        ], write=True)
        self.assertTrue(applied["applied"])
        html = (self.repo / "index.html").read_text()
        self.assertLess(html.index('id="two"'), html.index('id="one"'))
        self.assertEqual(readiness(self.repo, self.config)["score"], before + 10)

    def test_global_regression_overrides_one_platform_gain(self) -> None:
        query = "recent agent co-evolution"
        rows = []
        for provider, before, after in (("Doubao", 0, 1), ("DeepSeek", 1, 0)):
            for phase, value in (("before", before), ("after", after)):
                rows.append({"provider": provider, "query": query, "phase": phase,
                             "project_rank": str(value), "project_cited": str(value),
                             "target_mentioned": str(value), "paper_rank": "1",
                             "answer_accurate": "1"})
        result = compare_platforms(self.config, rows)
        self.assertLess(result["weighted_delta_known_cells"], 0)
        self.assertIn("DeepSeek", result["regressions"])
        self.assertNotEqual(result["verdict"], "keep")

    def test_missing_platform_is_unknown_not_zero(self) -> None:
        rows = [{"provider": "Doubao", "query": "recent agent co-evolution", "phase": "before",
                 "project_rank": "0", "paper_rank": "", "project_cited": "", "answer_accurate": ""}]
        result = compare_platforms(self.config, rows)
        self.assertEqual(result["observed_weight"], 0)
        self.assertEqual(result["global_delta_bounds"], [-1, 1])
        self.assertNotEqual(result["verdict"], "keep")


if __name__ == "__main__":
    unittest.main()
