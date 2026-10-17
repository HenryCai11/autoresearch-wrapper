"""Out-of-distribution signal: real visits, especially ones referred by AI engines.

Traffic lags site changes by days to weeks and is noisy, so it is never a
per-round metric. It is logged periodically to confirm, out of distribution,
that gains in the eval matrix show up with real visitors.

Currently supports GoatCounter. The token is read from a file and only ever
placed in a request header.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

AI_REFERRERS = {
    "chatgpt.com": "ChatGPT",
    "chat.openai.com": "ChatGPT",
    "perplexity.ai": "Perplexity",
    "www.perplexity.ai": "Perplexity",
    "gemini.google.com": "Gemini",
    "copilot.microsoft.com": "Copilot",
    "claude.ai": "Claude",
    "you.com": "You.com",
    "phind.com": "Phind",
    "kagi.com": "Kagi",
    "search.brave.com": "Brave",
    "duckduckgo.com": "DuckDuckGo",
}


class OODError(RuntimeError):
    pass


def _get(base: str, path: str, token: str, params: dict[str, str]) -> Any:
    url = f"{base.rstrip('/')}/{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise OODError(f"GoatCounter {path}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OODError(f"GoatCounter {path}: {type(exc).__name__}") from exc


def classify_referrer(name: str) -> str | None:
    host = urllib.parse.urlparse(name if "//" in name else f"//{name}").netloc.lower() or name.lower()
    host = host.split("/")[0]
    for domain, engine in AI_REFERRERS.items():
        if host == domain or host.endswith("." + domain):
            return engine
    return None


def goatcounter_snapshot(site_code: str, token_file: str | Path, days: int = 7) -> dict[str, Any]:
    """Fetch and summarise directly (needs internet access to GoatCounter)."""
    token = Path(token_file).expanduser().read_text().strip()
    base = f"https://{site_code}.goatcounter.com/api/v0"
    end = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - dt.timedelta(days=days)
    params = {"start": start.isoformat(), "end": end.isoformat()}
    return summarize_goatcounter(
        site_code,
        days,
        end.isoformat(),
        hits=_get(base, "stats/hits", token, {**params, "daily": "true"}),
        toprefs=_get(base, "stats/toprefs", token, params),
        total=_get(base, "stats/total", token, params),
    )


def snapshot_from_dir(site_code: str, directory: str | Path, days: int) -> dict[str, Any]:
    """Summarise responses saved by geo/scripts/fetch_goatcounter.sh (for hosts without internet)."""
    directory = Path(directory)

    def read(name: str) -> Any:
        path = directory / f"{name}.json"
        if not path.is_file():
            raise OODError(f"missing {path}; run geo/scripts/fetch_goatcounter.sh first")
        return json.loads(path.read_text())

    meta = json.loads((directory / "meta.json").read_text()) if (directory / "meta.json").is_file() else {}
    return summarize_goatcounter(
        site_code,
        int(meta.get("days", days)),
        meta.get("end", dt.datetime.now(dt.timezone.utc).isoformat()),
        hits=read("hits"),
        toprefs=read("toprefs"),
        total=read("total") if (directory / "total.json").is_file() else None,
    )


def summarize_goatcounter(
    site_code: str, days: int, end: str, *, hits: dict, toprefs: dict, total: dict | None
) -> dict[str, Any]:
    visits = int(total["total"]) if total and "total" in total else sum(int(i.get("count", 0)) for i in hits.get("hits", []))
    referrers = [{"name": item.get("name", ""), "count": int(item.get("count", 0))} for item in toprefs.get("stats", [])]
    ai: dict[str, int] = {}
    for item in referrers:
        engine = classify_referrer(item["name"])
        if engine:
            ai[engine] = ai.get(engine, 0) + item["count"]
    pages = sorted(
        ({"path": item.get("path"), "count": int(item.get("count", 0))} for item in hits.get("hits", [])),
        key=lambda page: -page["count"],
    )
    return {
        "recorded_at": end,
        "window_days": days,
        "site": site_code,
        "total_visits": visits,
        "ai_referred_visits": sum(ai.values()),
        "ai_referrers": ai,
        "top_referrers": referrers[:10],
        "top_pages": pages[:10],
    }
