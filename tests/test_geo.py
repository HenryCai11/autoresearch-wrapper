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
        self.config["interventions"] = [{"id": "edit-home", "nodes": ["section:one"], "cost": 1}]
        self.assertIn("outcome:Doubao:answer", prioritize(graph, self.config)[0]["reachable_outcomes"])

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
