"""Dependency-free clients for search APIs used by discovery probes.

Keys are accepted only through provider-specific environment variables or an
explicit key file.  They stay in request headers and are never included in
errors, answers, or probe records.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

TAVILY_ENDPOINT = "https://api.tavily.com/search"
EXA_ENDPOINT = "https://api.exa.ai/search"


class SearchAPIError(RuntimeError):
    pass


def load_search_api_key(provider: str, key_file: str | None = None) -> str:
    """Load a provider key without accepting it as a command-line argument."""
    settings = {
        "tavily": ("TAVILY_API_KEY", "TAVILY_API_KEY_FILE"),
        "exa": ("EXA_API_KEY", "EXA_API_KEY_FILE"),
    }
    if provider not in settings:
        raise SearchAPIError(f"unsupported search provider: {provider}")
    env_name, file_env_name = settings[provider]
    direct_key = (os.environ.get(env_name) or "").strip()
    configured_path = key_file
    if not configured_path and direct_key:
        return direct_key
    configured_path = configured_path or os.environ.get(file_env_name)
    if not configured_path:
        raise SearchAPIError(f"no API key: set {env_name} or {file_env_name}, or pass --api-key-file")
    path = Path(configured_path).expanduser()
    if not path.is_file():
        raise SearchAPIError(f"API key file does not exist: {path}")

    text = path.read_text().strip()
    for line in text.splitlines():
        name, separator, value = line.strip().removeprefix("export ").partition("=")
        if separator and name == env_name and value.strip():
            return value.strip().strip("'\"")
    if text and "\n" not in text and "=" not in text:
        return text
    raise SearchAPIError(f"API key file must contain a raw key or {env_name}=...")


def _post_json(
    endpoint: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    retries: int = 3,
    timeout: int = 60,
    open_url: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """POST JSON with bounded retries and deliberately secret-free errors."""
    open_url = open_url or urllib.request.urlopen
    body = json.dumps(payload).encode()
    last_error = "unknown error"
    attempts = max(1, retries)
    attempts_made = 0
    for attempt in range(attempts):
        attempts_made = attempt + 1
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with open_url(request, timeout=timeout) as response:
                decoded = json.loads(response.read().decode())
            if not isinstance(decoded, dict):
                raise SearchAPIError("search API returned a non-object response")
            return decoded
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code in (400, 401, 402, 403, 404, 422, 432, 433):
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
        if attempt + 1 < attempts:
            sleep(min(30, 2**attempt))
    raise SearchAPIError(f"search API request failed after {attempts_made} attempts: {last_error}")


def _result_text(result: dict[str, Any], fields: tuple[str, ...]) -> str:
    """Use the first available snippet representation, without duplicating content."""
    for field in fields:
        value = result.get(field)
        if isinstance(value, list):
            parts = [" ".join(str(item).split()) for item in value if str(item).strip()]
            if parts:
                return " ".join(parts)
        elif value is not None and str(value).strip():
            return " ".join(str(value).split())
    return ""


def format_ranked_results(payload: dict[str, Any], *, content_fields: tuple[str, ...]) -> str:
    """Turn a provider response into ordered text consumed by the shared judge."""
    results = payload.get("results")
    if not isinstance(results, list):
        raise SearchAPIError("search API response did not contain a results list")
    rendered: list[str] = []
    for index, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Untitled result").strip()
        url = str(item.get("url") or "").strip()
        content = _result_text(item, content_fields)
        heading = f"{index}. {title}"
        if content:
            heading += f" — {content}"
        lines = [heading]
        if url:
            lines.append(url)
        rendered.append("\n".join(lines))
    return "\n\n".join(rendered)


def search_tavily(
    query: str,
    *,
    api_key: str,
    search_depth: str = "basic",
    max_results: int = 10,
    timeout: int = 60,
    open_url: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    if search_depth not in {"basic", "advanced"}:
        raise SearchAPIError("Tavily search depth must be basic or advanced")
    if not 1 <= max_results <= 20:
        raise SearchAPIError("Tavily max results must be between 1 and 20")
    payload = _post_json(
        TAVILY_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}"},
        payload={
            "query": query,
            "topic": "general",
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        },
        timeout=timeout,
        open_url=open_url,
        sleep=sleep,
    )
    return format_ranked_results(payload, content_fields=("content",))


def search_exa(
    query: str,
    *,
    api_key: str,
    search_type: str = "auto",
    max_results: int = 10,
    timeout: int = 60,
    open_url: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    if search_type not in {"instant", "fast", "auto"}:
        raise SearchAPIError("Exa search type must be instant, fast, or auto")
    if not 1 <= max_results <= 100:
        raise SearchAPIError("Exa max results must be between 1 and 100")
    payload = _post_json(
        EXA_ENDPOINT,
        headers={"x-api-key": api_key},
        payload={
            "query": query,
            "type": search_type,
            "numResults": max_results,
            "contents": {"highlights": True},
        },
        timeout=timeout,
        open_url=open_url,
        sleep=sleep,
    )
    return format_ranked_results(payload, content_fields=("highlights", "text", "summary"))
