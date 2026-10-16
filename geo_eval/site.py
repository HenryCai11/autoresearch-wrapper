"""Read a website the way a crawler does: a built site directory or a live URL."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d])")
USER_AGENT = "geo-eval/0.1 (+https://github.com/HenryCai11/autoresearch-wrapper)"
# A built directory costs nothing to read; a live crawl makes one request per page.
MAX_DIR_PAGES = 500
MAX_CRAWL_PAGES = 60


@dataclass
class Page:
    path: str
    title: str = ""
    visible_text: str = ""
    hidden_text: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    canonical: str | None = None
    json_ld: list[dict] = field(default_factory=list)
    json_ld_errors: int = 0
    images: int = 0
    images_with_alt: int = 0
    links: list[str] = field(default_factory=list)

    def snippet(self, chars: int) -> str:
        """What a search result shows: title, meta description, and the opening text."""
        return " ".join(part for part in (self.title, self.meta.get("description", ""), self.visible_text[:chars]) if part)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(path="")
        self._stack: list[tuple[str, bool, bool]] = []  # (tag, skipped, hidden)
        self._visible: list[str] = []
        self._hidden: list[str] = []
        self._title: list[str] = []
        self._in_title = False
        self._ld_buffer: list[str] | None = None

    @property
    def _skipping(self) -> bool:
        return any(skipped for _, skipped, _ in self._stack)

    @property
    def _hiding(self) -> bool:
        return any(hidden for _, _, hidden in self._stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: (value or "") for key, value in attrs}
        if tag == "meta":
            key = attr.get("name") or attr.get("property")
            if key and "content" in attr:
                self.page.meta[key.lower()] = attr["content"]
        elif tag == "link" and "canonical" in attr.get("rel", "").lower().split():
            self.page.canonical = attr.get("href")
        elif tag == "img":
            self.page.images += 1
            if attr.get("alt", "").strip():
                self.page.images_with_alt += 1
        elif tag == "a" and attr.get("href"):
            self.page.links.append(attr["href"])
        elif tag == "title":
            self._in_title = True
        if tag == "script" and attr.get("type", "").lower() == "application/ld+json":
            self._ld_buffer = []
        if tag in VOID_TAGS:
            return
        hidden = "hidden" in attr or attr.get("aria-hidden") == "true" or bool(HIDDEN_STYLE.search(attr.get("style", "")))
        self._stack.append((tag, tag in SKIP_TAGS, hidden))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._ld_buffer is not None:
            self._add_json_ld("".join(self._ld_buffer))
            self._ld_buffer = None
        if tag in VOID_TAGS:
            return
        # Pop to the matching tag; tolerate sloppy HTML.
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._ld_buffer is not None:
            self._ld_buffer.append(data)
            return
        if self._in_title:
            self._title.append(data)
            return
        if self._skipping or not data.strip():
            return
        (self._hidden if self._hiding else self._visible).append(data.strip())

    def _add_json_ld(self, text: str) -> None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            self.page.json_ld_errors += 1
            return
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                self.page.json_ld.extend(x for x in item["@graph"] if isinstance(x, dict))
            elif isinstance(item, dict):
                self.page.json_ld.append(item)

    def result(self, path: str) -> Page:
        self.page.path = path
        self.page.title = " ".join("".join(self._title).split())
        self.page.visible_text = " ".join(self._visible)
        self.page.hidden_text = " ".join(self._hidden)
        return self.page


def parse_html(html: str, path: str = "/") -> Page:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return parser.result(path)


@dataclass
class Site:
    """A site snapshot: pages by URL path, plus the crawler-facing text files."""

    source: str
    pages: dict[str, Page]
    robots_txt: str | None = None
    llms_txt: str | None = None
    sitemap_xml: str | None = None

    @property
    def home(self) -> Page | None:
        return self.pages.get("/")

    def all_visible_text(self) -> str:
        return " ".join(page.visible_text for page in self.pages.values())

    def all_json_ld(self) -> list[dict]:
        return [item for page in self.pages.values() for item in page.json_ld]


def load_site(source: str, max_pages: int | None = None) -> Site:
    if re.match(r"^https?://", source):
        return _load_url(source, max_pages or MAX_CRAWL_PAGES)
    return _load_dir(Path(source), max_pages or MAX_DIR_PAGES)


def _url_path_for(file: Path, root: Path) -> str:
    rel = file.relative_to(root).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def _read_optional(path: Path) -> str | None:
    return path.read_text(errors="replace") if path.is_file() else None


def _load_dir(root: Path, max_pages: int) -> Site:
    if not (root / "index.html").is_file():
        raise FileNotFoundError(f"{root} has no index.html; build the site first")
    files = sorted(root.rglob("*.html"), key=lambda p: (p.relative_to(root).as_posix() != "index.html", len(p.parts), p.as_posix()))
    pages: dict[str, Page] = {}
    for file in files[:max_pages]:
        path = _url_path_for(file, root)
        pages[path] = parse_html(file.read_text(errors="replace"), path)
    return Site(
        source=str(root),
        pages=pages,
        robots_txt=_read_optional(root / "robots.txt"),
        llms_txt=_read_optional(root / "llms.txt"),
        sitemap_xml=_read_optional(root / "sitemap.xml"),
    )


def _fetch(url: str, timeout: int = 30) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _load_url(base: str, max_pages: int) -> Site:
    base = base if base.endswith("/") else base + "/"
    parsed_base = urllib.parse.urlparse(base)
    home_html = _fetch(base)
    if home_html is None:
        raise ConnectionError(f"could not fetch {base}")
    pages = {"/": parse_html(home_html, "/")}
    queue = list(pages["/"].links)
    while queue and len(pages) < max_pages:
        link = urllib.parse.urljoin(base, queue.pop(0))
        parsed = urllib.parse.urlparse(link)
        if parsed.netloc != parsed_base.netloc or parsed.path in pages:
            continue
        if re.search(r"\.(pdf|png|jpe?g|gif|svg|zip|ico|xml|txt)$", parsed.path, re.I):
            continue
        html = _fetch(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
        if html is None:
            continue
        pages[parsed.path] = parse_html(html, parsed.path)
        queue.extend(pages[parsed.path].links)
    return Site(
        source=base,
        pages=pages,
        robots_txt=_fetch(base + "robots.txt"),
        llms_txt=_fetch(base + "llms.txt"),
        sitemap_xml=_fetch(base + "sitemap.xml"),
    )
