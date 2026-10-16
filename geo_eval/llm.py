"""LLM comprehension test: can a model answer questions about the entity from the site alone?

The model sees what a crawler-based answer engine would ingest (homepage text,
llms.txt, other pages) and answers every map question in one call. Answers are
graded by matching the map's answer terms, so grading needs no second model.

Any OpenAI-compatible chat endpoint works. Defaults target Aleph on Vulcan;
the key comes from GEO_LLM_API_KEY, TYK_KEY, or ~/.aleph_tyk.env and is never
printed or written anywhere.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .kmap import KnowledgeMap, contains_any
from .site import Site

DEFAULT_BASE_URL = "https://inference.vulcan.alliancecan.ca/v1"
DEFAULT_MODEL = "gpt-oss-120b"
CONTEXT_CHARS = 14000
SYSTEM_PROMPT = (
    "You answer questions using ONLY the provided web pages. If a page does not state the "
    "answer, reply exactly \"unknown\". Never use outside knowledge."
)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    score: float
    by_hop: dict[int, float]
    answers: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "by_hop": self.by_hop, "answers": self.answers, "model": self.model}


def build_context(site: Site, budget: int = CONTEXT_CHARS) -> str:
    """Homepage first, then llms.txt, then other pages, as an answer engine would weigh them."""
    blocks: list[str] = []
    if site.home:
        blocks.append(f"[page {site.source.rstrip('/')}/]\n{site.home.title}\n{site.home.visible_text}")
    if site.llms_txt:
        blocks.append(f"[file /llms.txt]\n{site.llms_txt}")
    for path, page in site.pages.items():
        if path != "/":
            blocks.append(f"[page {path}]\n{page.title}\n{page.visible_text}")
    context, used = [], 0
    for block in blocks:
        if used >= budget:
            break
        context.append(block[: budget - used])
        used += len(context[-1])
    return "\n\n".join(context)


def build_prompt(kmap: KnowledgeMap, context: str) -> str:
    questions = "\n".join(f"{q.id}: {q.q}" for q in kmap.questions)
    return (
        f"Web pages:\n<<<\n{context}\n>>>\n\n"
        "Answer each question below from the pages only. Reply with a JSON object mapping "
        "each question id to a short answer string (\"unknown\" if not stated). No other text.\n\n"
        f"{questions}"
    )


def grade(kmap: KnowledgeMap, answers: dict[str, str], model: str = "") -> LLMResult:
    graded, totals, correct = [], {}, {}
    for question in kmap.questions:
        answer = str(answers.get(question.id, "")).strip()
        ok = answer.lower() != "unknown" and contains_any(answer, question.answer_terms)
        totals[question.hop] = totals.get(question.hop, 0) + 1
        correct[question.hop] = correct.get(question.hop, 0) + int(ok)
        graded.append(
            {"id": question.id, "node": question.node, "hop": question.hop, "q": question.q, "answer": answer, "correct": ok}
        )
    by_hop = {hop: round(correct[hop] / totals[hop], 4) for hop in sorted(totals)}
    # Weight hops like the map does: the core matters most.
    weights = {0: 3.0, 1: 2.0, 2: 1.0}
    denominator = sum(weights.get(hop, 1.0) * totals[hop] for hop in totals) or 1
    numerator = sum(weights.get(hop, 1.0) * correct[hop] for hop in totals)
    return LLMResult(score=round(100 * numerator / denominator, 2), by_hop=by_hop, answers=graded, model=model)


def parse_answers(content: str) -> dict[str, str]:
    """Pull the JSON object out of a reply that may include code fences or prose."""
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        raise LLMError("model reply contained no JSON object")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError(f"model reply was not valid JSON: {exc}") from exc
    return {str(key): str(value) for key, value in data.items()}


def load_api_key() -> str:
    for name in ("GEO_LLM_API_KEY", "TYK_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    env_file = Path(os.environ.get("GEO_LLM_KEY_FILE", "~/.aleph_tyk.env")).expanduser()
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, _, value = line.strip().removeprefix("export ").partition("=")
            if key == "TYK_KEY" and value:
                return value.strip().strip("'\"")
    raise LLMError("no API key: set GEO_LLM_API_KEY or TYK_KEY, or provide ~/.aleph_tyk.env")


def chat(
    prompt: str,
    *,
    model: str,
    base_url: str,
    api_key: str,
    retries: int = 3,
    timeout: int = 180,
    sleep: Callable[[float], None] = time.sleep,
    system: str | None = SYSTEM_PROMPT,
) -> str:
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages.insert(0, {"role": "system", "content": system})
    request_body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0, "max_tokens": 4096}
    if model.startswith("gpt-oss"):
        request_body["reasoning_effort"] = "low"  # gpt-oss specific; other servers may reject it
    body = json.dumps(request_body).encode()
    last_error = ""
    for attempt in range(retries):
        request = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode())
            content = payload["choices"][0]["message"].get("content") or ""
            if content.strip():
                return content
            last_error = "empty reply"
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"  # never echo request headers
            if exc.code in (400, 401, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
        sleep(min(60, 5 * 2**attempt))
    raise LLMError(f"LLM request failed after {retries} attempts: {last_error}")


def score_llm(
    site: Site,
    kmap: KnowledgeMap,
    *,
    model: str | None = None,
    base_url: str | None = None,
    samples: int = 1,
    ask: Callable[[str], str] | None = None,
) -> LLMResult:
    """Score comprehension; `samples` > 1 averages several replies to damp model noise."""
    if not kmap.questions:
        raise LLMError("knowledge map has no questions")
    model = model or os.environ.get("GEO_LLM_MODEL", DEFAULT_MODEL)
    if ask is None:
        base = base_url or os.environ.get("GEO_LLM_BASE_URL", DEFAULT_BASE_URL)
        key = load_api_key()
        ask = lambda prompt: chat(prompt, model=model, base_url=base, api_key=key)  # noqa: E731
    prompt = build_prompt(kmap, build_context(site))
    results = [grade(kmap, parse_answers(ask(prompt)), model) for _ in range(max(1, samples))]
    if len(results) == 1:
        return results[0]
    by_hop = {hop: round(sum(r.by_hop.get(hop, 0) for r in results) / len(results), 4) for hop in results[0].by_hop}
    return LLMResult(
        score=round(sum(r.score for r in results) / len(results), 2),
        by_hop=by_hop,
        answers=results[0].answers,
        model=model,
    )
