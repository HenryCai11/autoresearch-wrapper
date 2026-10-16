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
from geo_eval.discovery import build_discovery, judge_answer
from geo_eval.kmap import MapError, contains_term, parse_map
from geo_eval.llm import LLMError, build_context, chat, grade, load_api_key, parse_answers, score_llm
from geo_eval.matrix import build_matrix
from geo_eval.offline import robots_blocks, score_technical
from geo_eval.ood import classify_referrer
from geo_eval.search_api import (
    EXA_ENDPOINT,
    TAVILY_ENDPOINT,
    SearchAPIError,
    load_search_api_key,
    search_exa,
    search_tavily,
)
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

    def test_load_dir_reads_every_page_of_a_large_site(self) -> None:
        extras = {f"p{i}/index.html": f"<html><head><title>Page {i}</title></head><body>x</body></html>" for i in range(80)}
        site = load_site(str(write_site(self.tmp / "big", extras=extras)))
        self.assertEqual(len(site.pages), 81)

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
        self.assertIn("node,keyword,hop,kind,site,snippet,schema,llms,llm,search", matrix.to_csv())
        self.assertIsNone(row["affiliation"].cells["snippet"])  # v1: not measured

    def test_metric_v2_snippets_and_scholarly_checks(self) -> None:
        # A paper page with Google Scholar tags, and a homepage whose opening text is short.
        paper_page = (
            '<html><head><title>Notes on the Analytical Engine</title>'
            '<meta name="citation_title" content="Notes on the Analytical Engine">'
            '<meta name="citation_author" content="Ada Lovelace"></head><body><p>1843 notes.</p></body></html>'
        )
        site = load_site(str(full_site(self.tmp / "v2")))
        technical_v1 = score_technical(site, self.kmap)
        technical_v2 = score_technical(site, self.kmap, version=2)
        self.assertNotIn("scholarly", technical_v1.categories)
        checks = {c.name: c.value for c in technical_v2.checks}
        self.assertEqual(checks["paper_pages"], 0.0)  # /papers/ is titled "Papers", not the paper
        self.assertEqual(checks["scholar_meta"], 0.0)
        tagged = load_site(str(write_site(self.tmp / "v2b", extras={"notes/index.html": paper_page})))
        checks = {c.name: c.value for c in score_technical(tagged, self.kmap, version=2).checks}
        self.assertEqual(checks["paper_pages"], 1.0)
        self.assertEqual(checks["scholar_meta"], 1.0)
        self.assertEqual(checks["identity_front_loaded"], 1.0)

        # Snippet column: only title, description and the opening text count.
        matrix = build_matrix(site, self.kmap, snippet_chars=40)
        cells = {r.node: r.cells for r in matrix.rows}
        self.assertEqual(cells["affiliation"]["snippet"], 1.0)  # in the meta description
        self.assertEqual(cells["programming"]["snippet"], 0.0)  # only deep in the page
        self.assertEqual(cells["programming"]["site"], 1.0)
        self.assertNotIn("first computer program", build_context(site, 4000, snippet_chars=40).split("[file /llms.txt]")[0])

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

    def test_search_column_ignores_memory_models(self) -> None:
        site = load_site(str(full_site(self.tmp / "site")))
        probes = [
            {"query": "first computer program", "found": False, "recorded_at": "2026-02-01T00:00:00", "engine": "web"},
            {"query": "first computer program", "found": True, "recorded_at": "2026-02-01T00:00:00", "engine": "memory:m"},
        ]
        cells = {r.node: r.cells for r in build_matrix(site, self.kmap, probes=probes).rows}
        self.assertEqual(cells["programming"]["search"], 0.0)

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

    # -- hosted search APIs -------------------------------------------------

    def test_search_api_key_lookup_uses_env_or_explicit_file(self) -> None:
        key_file = self.tmp / "exa-key"
        key_file.write_text("EXA_API_KEY='file-key'\n")
        with mock.patch.dict(os.environ, {"TAVILY_API_KEY": "env-key"}, clear=True):
            self.assertEqual(load_search_api_key("tavily"), "env-key")
        with mock.patch.dict(os.environ, {"EXA_API_KEY": "stale-env-key"}, clear=True):
            self.assertEqual(load_search_api_key("exa", str(key_file)), "file-key")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SearchAPIError):
                load_search_api_key("tavily")

    def test_tavily_and_exa_search_format_ranked_results(self) -> None:
        class Response:
            def __init__(self, payload: dict) -> None:
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(self.payload).encode()

        calls: list[tuple[str, dict, dict]] = []

        def tavily_open(request, timeout: int):
            calls.append((request.full_url, dict(request.header_items()), json.loads(request.data)))
            self.assertEqual(timeout, 12)
            return Response({"results": [
                {"title": "Babbage", "url": "https://babbage.example/", "content": "Other result"},
                {"title": "Ada", "url": "https://ada.example/", "content": "Analytical Society"},
            ]})

        tavily_text = search_tavily(
            "Ada", api_key="tavily-test-key", search_depth="basic", max_results=2,
            timeout=12, open_url=tavily_open,
        )
        self.assertIn("1. Babbage", tavily_text)
        self.assertIn("2. Ada", tavily_text)
        self.assertEqual(judge_answer(tavily_text, self.kmap).rank, 2)
        self.assertEqual(calls[0][0], TAVILY_ENDPOINT)
        self.assertEqual({k.lower(): v for k, v in calls[0][1].items()}["authorization"], "Bearer tavily-test-key")
        self.assertEqual(calls[0][2]["include_answer"], False)

        def exa_open(request, timeout: int):
            calls.append((request.full_url, dict(request.header_items()), json.loads(request.data)))
            self.assertEqual(timeout, 13)
            return Response({"results": [
                {"title": "Ada", "url": "https://ada.example/", "highlights": ["Analytical Society"]},
            ]})

        exa_text = search_exa(
            "Ada", api_key="exa-test-key", search_type="auto", max_results=3,
            timeout=13, open_url=exa_open,
        )
        self.assertIn("Analytical Society", exa_text)
        self.assertEqual(judge_answer(exa_text, self.kmap).rank, 1)
        self.assertEqual(calls[1][0], EXA_ENDPOINT)
        self.assertEqual({k.lower(): v for k, v in calls[1][1].items()}["x-api-key"], "exa-test-key")
        self.assertEqual(calls[1][2], {
            "query": "Ada", "type": "auto", "numResults": 3, "contents": {"highlights": True},
        })

    def test_search_api_errors_do_not_leak_keys(self) -> None:
        import urllib.error

        error = urllib.error.HTTPError("u", 401, "unauthorised", {}, None)
        with self.assertRaises(SearchAPIError) as exc:
            search_tavily(
                "Ada", api_key="never-print-this", open_url=mock.Mock(side_effect=error), sleep=lambda _seconds: None,
            )
        self.assertIn("HTTP 401", str(exc.exception))
        self.assertNotIn("never-print-this", str(exc.exception))

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

    def test_cli_tavily_and_exa_probes_share_discovery_judging(self) -> None:
        map_path = self.tmp / "map.json"
        map_path.write_text(json.dumps(MAP))
        probes = self.tmp / "probes.jsonl"
        tavily_answers = self.tmp / "tavily.jsonl"
        exa_answers = self.tmp / "exa.jsonl"

        def fake_search(query: str, **_kwargs) -> str:
            if query == "Ada Lovelace Analytical Society":
                return "1. Ada Lovelace\nhttps://ada.example/\nAnalytical Society"
            return "1. No relevant result\nhttps://unrelated.example/"

        with mock.patch("geo_eval.cli.load_search_api_key", return_value="runtime-only-key"), mock.patch(
            "geo_eval.cli.search_tavily", side_effect=fake_search
        ) as tavily:
            code, out = self.run_cli(
                "probe-tavily", "--map", str(map_path), "--probes", str(probes),
                "--answers", str(tavily_answers), "--max-results", "5",
            )
        self.assertEqual(code, 0)
        self.assertEqual(tavily.call_count, 5)
        self.assertIn("tavily-search\tfound (rank 1)\tAda Lovelace Analytical Society", out)

        with mock.patch("geo_eval.cli.load_search_api_key", return_value="runtime-only-key"), mock.patch(
            "geo_eval.cli.search_exa", side_effect=fake_search
        ) as exa:
            code, out = self.run_cli(
                "probe-exa", "--map", str(map_path), "--probes", str(probes),
                "--answers", str(exa_answers), "--search-type", "fast",
            )
        self.assertEqual(code, 0)
        self.assertEqual(exa.call_count, 5)
        self.assertIn("exa-search\tfound (rank 1)\tAda Lovelace Analytical Society", out)

        records = [json.loads(line) for line in probes.read_text().splitlines()]
        self.assertEqual(len(records), 10)
        self.assertEqual({record["engine"] for record in records}, {"tavily-search", "exa-search"})
        self.assertNotIn("runtime-only-key", probes.read_text() + tavily_answers.read_text() + exa_answers.read_text())

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

    # -- discovery matrix ----------------------------------------------------

    def test_judge_ranks_cited_site_and_requires_same_sentence_attribution(self) -> None:
        cited = judge_answer(
            "1. Babbage page https://babbage.example/x\n2. **Ada Lovelace**, see https://www.ada.example/notes.",
            self.kmap,
        )
        self.assertTrue(cited.found and cited.site_cited)
        self.assertEqual(cited.rank, 2)
        self.assertEqual(cited.url, "https://www.ada.example/notes")

        attributed = judge_answer(
            "Ada Lovelace is a member of the Analytical Society. She worked with Charles Babbage.", self.kmap
        )
        self.assertTrue(attributed.found and attributed.attributed and not attributed.site_cited)

        # Echoing the query's affiliation and inventing the rest is not finding the entity.
        query = "Ada Lovelace Analytical Society"
        hallucinated = judge_answer("Ada Lovelace, Analytical Society: professor of chemistry and botany.", self.kmap, query)
        self.assertFalse(hallucinated.found)
        # Core facts are guessable from the query, so they do not corroborate.
        guessed = judge_answer("Ada Lovelace, Analytical Society: a mathematician and chemist.", self.kmap, query)
        self.assertFalse(guessed.found)
        # A true fact the query did not contain corroborates it.
        corroborated = judge_answer("Ada Lovelace, Analytical Society; wrote the first computer program.", self.kmap, query)
        self.assertTrue(corroborated.found)

        split = judge_answer("Ada Lovelace wrote notes.\nThe Analytical Society met in London.", self.kmap)
        self.assertFalse(split.found)
        similar = judge_answer("Ada Byron-King of the Analytical Society.", self.kmap)
        self.assertFalse(similar.found)

    def test_discovery_matrix_uses_latest_record_per_engine(self) -> None:
        probes = [
            {"query": "first computer program", "engine": "web", "found": False, "rank": None, "recorded_at": "2026-01-01T00:00:00"},
            {"query": "first computer program", "engine": "web", "found": True, "rank": 2, "recorded_at": "2026-02-01T00:00:00"},
            {"query": "Ada Lovelace Analytical Society", "engine": "memory:m", "found": True, "rank": None, "recorded_at": "2026-02-01T00:00:00"},
            {"query": "an extra query", "engine": "web", "found": False, "rank": None, "recorded_at": "2026-02-01T00:00:00"},
        ]
        matrix = build_discovery(self.kmap, probes)
        self.assertEqual(matrix.engines, ["web"])
        self.assertEqual(matrix.cells[("first computer program", "web")], {"found": True, "rank": 2, "url": None})
        self.assertNotIn(("first computer program", "memory:m"), matrix.cells)
        self.assertIn("an extra query", [row["query"] for row in matrix.rows])
        summary = matrix.summary()
        self.assertEqual((summary["web"]["found"], summary["web"]["probed"]), (1, 2))
        self.assertNotIn("memory:m", summary)
        self.assertIn("| first computer program | 2 | ✓2 |", matrix.to_markdown())

    def test_cli_probe_judge_and_discovery(self) -> None:
        map_path = self.tmp / "map.json"
        map_path.write_text(json.dumps(MAP))
        answers = self.tmp / "answers.jsonl"
        answers.write_text(
            json.dumps({"query": "first computer program", "text": "1. https://ada.example/ - Ada Lovelace"}) + "\n"
            + json.dumps({"query": "Charles Babbage", "text": "Charles Babbage, mathematician."}) + "\n"
        )
        probes = self.tmp / "probes.jsonl"
        code, out = self.run_cli("probe-judge", "--map", str(map_path), "--probes", str(probes), "--answers", str(answers), "--engine", "codex-search")
        self.assertEqual(code, 0)
        self.assertIn("found (rank 1)", out)
        records = [json.loads(line) for line in probes.read_text().splitlines()]
        self.assertEqual([r["found"] for r in records], [True, False])
        code, out = self.run_cli("discovery", "--map", str(map_path), "--probes", str(probes))
        self.assertIn("ENGINE codex-search: found 1/2", out)

    def test_geo_launcher_finds_toolkit_through_symlink(self) -> None:
        home = Path(tempfile.mkdtemp(prefix="geo-home-"))
        link = home / "geo-autoresearch"
        link.symlink_to(REPO_ROOT / "skills" / "geo-autoresearch", target_is_directory=True)
        result = subprocess.run(["bash", str(link / "geo.sh"), "root"], capture_output=True, text=True, check=True)
        self.assertEqual(Path(result.stdout.strip()).resolve(), REPO_ROOT.resolve())


if __name__ == "__main__":
    unittest.main()
