from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geo_eval import cli
from geo_eval.kmap import MapError, contains_term, parse_map
from geo_eval.llm import LLMError, build_context, chat, grade, load_api_key, parse_answers, score_llm
from geo_eval.matrix import build_matrix
from geo_eval.offline import robots_blocks, score_technical
from geo_eval.ood import classify_referrer
from geo_eval.site import load_site, parse_html

MAP = {
    "entity": {"name": "Ada Lovelace", "aliases": ["Augusta Ada King"], "url": "https://ada.example/"},
    "nodes": [
        {"id": "affiliation", "hop": 0, "terms": ["Analytical Society"]},
        {"id": "role", "hop": 0, "terms": ["mathematician"]},
        {"id": "notes", "hop": 1, "kind": "paper", "terms": ["Notes on the Analytical Engine"], "venue": "1843"},
        {"id": "babbage", "hop": 1, "terms": ["Charles Babbage"]},
        {"id": "programming", "hop": 2, "kind": "topic", "terms": ["first computer program"], "via": ["notes"]},
    ],
    "questions": [
        {"id": "q-aff", "node": "affiliation", "q": "Which society?", "answer_terms": ["Analytical Society"]},
        {"id": "q-notes", "node": "notes", "q": "When were the Notes published?", "answer_terms": ["1843"]},
        {"id": "q-prog", "node": "programming", "q": "What did she write first?", "answer_terms": ["program"]},
    ],
    "forbidden": [{"text": "Lorem ipsum", "reason": "template"}],
    "limits": {"max_visible_chars": 2000},
}

GOOD_HOME = """<!doctype html><html><head>
<title>Ada Lovelace - mathematician</title>
<meta name="description" content="Ada Lovelace is a mathematician of the Analytical Society who wrote the Notes on the Analytical Engine.">
<meta property="og:title" content="Ada Lovelace"><meta property="og:description" content="Mathematician">
<link rel="canonical" href="https://ada.example/">
<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [
 {"@type": "Person", "name": "Ada Lovelace", "alternateName": ["Augusta Ada King"], "url": "https://ada.example/",
  "sameAs": ["https://a", "https://b", "https://c"], "affiliation": {"name": "Analytical Society"}, "jobTitle": "mathematician"},
 {"@type": "ScholarlyArticle", "name": "Notes on the Analytical Engine", "author": "Ada Lovelace"}]}</script>
<style>.x{}</style></head><body>
<nav aria-hidden="true">Ada Lovelace menu</nav>
<h1>Ada Lovelace (Augusta Ada King)</h1>
<p>I am a mathematician in the Analytical Society, working with Charles Babbage.</p>
<p>My Notes on the Analytical Engine (1843) contain the first computer program.</p>
<img src="a.png" alt="portrait"><img src="b.png">
<script>var hidden = "first computer program";</script>
</body></html>"""


def write_site(root: Path, home: str = GOOD_HOME, extras: dict[str, str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(home)
    for name, text in (extras or {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def full_site(root: Path) -> Path:
    return write_site(
        root,
        extras={
            "llms.txt": "# Ada Lovelace\nMathematician, Analytical Society. Notes on the Analytical Engine. Charles Babbage. first computer program.\n",
            "robots.txt": "User-agent: *\nAllow: /\nSitemap: https://ada.example/sitemap.xml\n",
            "sitemap.xml": "<urlset><url><loc>https://ada.example/</loc></url></urlset>",
            "papers/index.html": "<html><head><title>Papers</title></head><body><p>Notes on the Analytical Engine</p></body></html>",
        },
    )


class GeoEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kmap = parse_map(MAP)
        self.tmp = Path(tempfile.mkdtemp(prefix="geo-eval-"))

    # -- knowledge map ------------------------------------------------------

    def test_map_validation_errors(self) -> None:
        with self.assertRaises(MapError):
            parse_map({"entity": {}})
        with self.assertRaises(MapError):
            parse_map({**MAP, "nodes": [{"id": "a", "hop": 3, "terms": ["x"]}]})
        with self.assertRaises(MapError):
            parse_map({**MAP, "nodes": [{"id": "a", "hop": 1, "terms": ["x"], "via": ["missing"]}]})
        with self.assertRaises(MapError):
            parse_map({**MAP, "questions": [{"q": "?", "answer_terms": ["x"], "node": "nope"}]})

    def test_default_queries_by_hop(self) -> None:
        self.assertEqual(self.kmap.queries_for(self.kmap.node("affiliation")), ["Ada Lovelace Analytical Society"])
        self.assertEqual(self.kmap.queries_for(self.kmap.node("programming")), ["first computer program"])

    def test_term_matching_is_forgiving(self) -> None:
        self.assertTrue(contains_term("Environment–Agent  co-evolution", "environment-agent co-evolution"))

    # -- site reading -------------------------------------------------------

    def test_parse_html_separates_visible_hidden_and_structured(self) -> None:
        page = parse_html(GOOD_HOME)
        self.assertIn("Charles Babbage", page.visible_text)
        self.assertNotIn("var hidden", page.visible_text)
        self.assertIn("Ada Lovelace menu", page.hidden_text)
        self.assertEqual(page.title, "Ada Lovelace - mathematician")
        self.assertEqual(page.canonical, "https://ada.example/")
        self.assertEqual({item["@type"] for item in page.json_ld}, {"Person", "ScholarlyArticle"})
        self.assertEqual((page.images, page.images_with_alt), (2, 1))

    def test_load_dir_requires_built_site(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_site(str(self.tmp / "empty"))
        site = load_site(str(full_site(self.tmp / "site")))
        self.assertEqual(set(site.pages), {"/", "/papers/"})
        self.assertIsNotNone(site.llms_txt)

    # -- matrix and technical checks ----------------------------------------

    def test_matrix_cells_and_scores(self) -> None:
        site = load_site(str(full_site(self.tmp / "site")))
        matrix = build_matrix(site, self.kmap)
        row = {r.node: r for r in matrix.rows}
        self.assertEqual(row["affiliation"].cells["site"], 1.0)
        self.assertEqual(row["affiliation"].cells["schema"], 1.0)
        self.assertEqual(row["babbage"].cells["schema"], 0.0)
        self.assertIsNone(row["notes"].cells["llm"])
        self.assertIsNone(row["notes"].cells["search"])
        self.assertGreater(matrix.offline_score(), 80)
        self.assertIn("| Analytical Society | 0 |", matrix.to_markdown())
        self.assertIn("node,keyword,hop,kind,site,schema,llms,llm,search", matrix.to_csv())

    def test_hop0_must_be_on_homepage(self) -> None:
        home = GOOD_HOME.replace("in the Analytical Society", "").replace("of the Analytical Society", "")
        site = load_site(str(write_site(self.tmp / "s", home, {"about/index.html": "<p>Analytical Society</p>"})))
        cells = {r.node: r.cells for r in build_matrix(site, self.kmap).rows}
        self.assertEqual(cells["affiliation"]["site"], 0.0)

    def test_search_column_uses_latest_probe_per_query(self) -> None:
        site = load_site(str(full_site(self.tmp / "site")))
        probes = [
            {"query": "first computer program", "found": False, "recorded_at": "2026-01-01T00:00:00", "engine": "web"},
            {"query": "First computer program", "found": True, "recorded_at": "2026-02-01T00:00:00", "engine": "web"},
        ]
        cells = {r.node: r.cells for r in build_matrix(site, self.kmap, probes=probes).rows}
        self.assertEqual(cells["programming"]["search"], 1.0)

    def test_technical_full_vs_bare_site(self) -> None:
        good = score_technical(load_site(str(full_site(self.tmp / "good"))), self.kmap)
        bare = score_technical(load_site(str(write_site(self.tmp / "bare", "<html><body><p>Lorem ipsum</p></body></html>"))), self.kmap)
        self.assertGreater(good.score, 85)
        self.assertLess(bare.score, 25)
        failed = {c.name for c in bare.checks if c.value < 1}
        self.assertTrue({"person_jsonld", "llms_txt", "canonical", "no_forbidden_text"} <= failed)

    def test_robots_blocking(self) -> None:
        robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        self.assertTrue(robots_blocks(robots, "GPTBot"))
        self.assertFalse(robots_blocks(robots, "ClaudeBot"))
        self.assertTrue(robots_blocks("User-agent: *\nDisallow: /\n", "PerplexityBot"))

    def test_guardrails_flag_stuffing_and_padding_but_not_theme_duplicates(self) -> None:
        site = load_site(str(full_site(self.tmp / "ok")))
        self.assertEqual(score_technical(site, self.kmap).guardrail_violations, [])

        stuffed = GOOD_HOME.replace("</body>", '<div style="display:none">Lovelace Prize winner Charles Babbage</div></body>')
        stuffed = stuffed.replace("working with Charles Babbage", "")
        violations = score_technical(load_site(str(write_site(self.tmp / "stuffed", stuffed))), self.kmap).guardrail_violations
        self.assertTrue(any("hidden" in v for v in violations))

        padded = GOOD_HOME.replace("</body>", "<p>" + "filler " * 400 + "</p></body>")
        violations = score_technical(load_site(str(write_site(self.tmp / "padded", padded))), self.kmap).guardrail_violations
        self.assertTrue(any("exceeds limit" in v for v in violations))

    # -- LLM comprehension --------------------------------------------------

    def test_grade_and_parse_answers(self) -> None:
        answers = parse_answers('```json\n{"q-aff": "The Analytical Society", "q-notes": "unknown", "q-prog": "a program"}\n```')
        result = grade(self.kmap, answers)
        self.assertEqual([a["correct"] for a in result.answers], [True, False, True])
        self.assertEqual(result.by_hop, {0: 1.0, 1: 0.0, 2: 1.0})
        # weights 3/2/1 -> (3 + 0 + 1) / 6
        self.assertAlmostEqual(result.score, 66.67, places=2)
        with self.assertRaises(LLMError):
            parse_answers("no json here")

    def test_score_llm_uses_site_context_and_averages_samples(self) -> None:
        site = load_site(str(full_site(self.tmp / "site")))
        prompts: list[str] = []
        replies = iter(['{"q-aff": "Analytical Society", "q-notes": "1843", "q-prog": "program"}', '{"q-aff": "no idea"}'])

        def ask(prompt: str) -> str:
            prompts.append(prompt)
            return next(replies)

        result = score_llm(site, self.kmap, samples=2, ask=ask)
        self.assertIn("Charles Babbage", prompts[0])
        self.assertIn("[file /llms.txt]", prompts[0])
        self.assertEqual(result.score, 50.0)
        self.assertLess(len(build_context(site, budget=100)), 120)

    def test_api_key_lookup_never_needs_the_real_file(self) -> None:
        key_file = self.tmp / "aleph.env"
        key_file.write_text("export TYK_KEY='secret-value'\n")
        with mock.patch.dict(os.environ, {"GEO_LLM_KEY_FILE": str(key_file)}, clear=True):
            self.assertEqual(load_api_key(), "secret-value")
        with mock.patch.dict(os.environ, {"GEO_LLM_KEY_FILE": str(self.tmp / "missing")}, clear=True):
            with self.assertRaises(LLMError):
                load_api_key()

    def test_chat_retries_then_reports_without_leaking_key(self) -> None:
        import urllib.error

        error = urllib.error.HTTPError("u", 503, "busy", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(LLMError) as exc:
                chat("hi", model="m", base_url="https://x/v1", api_key="secret-value", retries=2, sleep=lambda s: None)
        self.assertIn("HTTP 503", str(exc.exception))
        self.assertNotIn("secret-value", str(exc.exception))

    # -- CLI ----------------------------------------------------------------

    def run_cli(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(list(args))
        return code, out.getvalue()

    def test_cli_matrix_prints_metric_and_report(self) -> None:
        map_path = self.tmp / "map.json"
        map_path.write_text(json.dumps(MAP))
        site = full_site(self.tmp / "site")
        report = self.tmp / "report.json"
        code, out = self.run_cli("matrix", "--map", str(map_path), "--site", str(site), "--no-llm", "--report", str(report))
        self.assertEqual(code, 0)
        metric = float(out.strip().splitlines()[-1].split("=")[1])
        self.assertGreater(metric, 80)
        self.assertEqual(json.loads(report.read_text())["metric"], metric)

    def test_cli_guardrail_exits_without_metric(self) -> None:
        map_path = self.tmp / "map.json"
        map_path.write_text(json.dumps(MAP))
        padded = write_site(self.tmp / "padded", GOOD_HOME.replace("</body>", "<p>" + "filler " * 400 + "</p></body>"))
        code, out = self.run_cli("matrix", "--map", str(map_path), "--site", str(padded), "--no-llm")
        self.assertEqual(code, cli.EXIT_GUARDRAIL)
        self.assertIn("GUARDRAIL:", out)
        self.assertNotIn("METRIC=", out)

    def test_cli_probe_record_feeds_search_column(self) -> None:
        map_path = self.tmp / "map.json"
        map_path.write_text(json.dumps(MAP))
        probes = self.tmp / "probes.jsonl"
        self.run_cli("probe-record", "--probes", str(probes), "--query", "first computer program", "--found", "--engine", "web")
        code, out = self.run_cli("queries", "--map", str(map_path))
        self.assertIn("first computer program", out)
        code, out = self.run_cli(
            "matrix", "--map", str(map_path), "--site", str(full_site(self.tmp / "site")), "--no-llm",
            "--probes", str(probes), "--format", "json",
        )
        report = json.loads(out[: out.rindex("}") + 1])
        rows = {row["node"]: row for row in report["matrix"]["rows"]}
        self.assertEqual(rows["programming"]["cells"]["search"], 1.0)

    def test_instance_map_is_valid(self) -> None:
        code, out = self.run_cli("validate", "--map", str(REPO_ROOT / "geo" / "instances" / "henrycai11" / "map.json"))
        self.assertEqual(code, 0)
        self.assertIn("entity: Min Cai", out)

    # -- out-of-distribution -------------------------------------------------

    def test_ai_referrer_classification(self) -> None:
        self.assertEqual(classify_referrer("https://chatgpt.com/"), "ChatGPT")
        self.assertEqual(classify_referrer("www.perplexity.ai"), "Perplexity")
        self.assertIsNone(classify_referrer("https://scholar.google.com/"))

    def test_ood_summary_from_saved_responses(self) -> None:
        saved = self.tmp / "gc"
        saved.mkdir()
        (saved / "hits.json").write_text(json.dumps({"hits": [{"path": "/", "count": 5}, {"path": "/cv/", "count": 2}]}))
        (saved / "toprefs.json").write_text(json.dumps({"stats": [
            {"name": "chatgpt.com", "count": 2}, {"name": "www.perplexity.ai", "count": 1}, {"name": "github.com", "count": 3},
        ]}))
        (saved / "total.json").write_text(json.dumps({"total": 7}))
        (saved / "meta.json").write_text(json.dumps({"days": 7, "end": "2026-10-15T00:00:00Z"}))
        log = self.tmp / "ood.jsonl"
        code, out = self.run_cli("ood", "--goatcounter", "site", "--input-dir", str(saved), "--log", str(log))
        self.assertEqual(code, 0)
        snapshot = json.loads(log.read_text().splitlines()[0])
        self.assertEqual(snapshot["total_visits"], 7)
        self.assertEqual(snapshot["ai_referred_visits"], 3)
        self.assertEqual(snapshot["ai_referrers"], {"ChatGPT": 2, "Perplexity": 1})
        self.assertEqual(snapshot["top_pages"][0], {"path": "/", "count": 5})

    def test_geo_launcher_finds_toolkit_through_symlink(self) -> None:
        home = Path(tempfile.mkdtemp(prefix="geo-home-"))
        link = home / "geo-autoresearch"
        link.symlink_to(REPO_ROOT / "skills" / "geo-autoresearch", target_is_directory=True)
        result = subprocess.run(["bash", str(link / "geo.sh"), "root"], capture_output=True, text=True, check=True)
        self.assertEqual(Path(result.stdout.strip()).resolve(), REPO_ROOT.resolve())


if __name__ == "__main__":
    unittest.main()
