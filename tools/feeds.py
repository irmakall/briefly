"""Read RSS/Atom feeds and turn every entry into one common format (FR-28)."""
import html
import re
from datetime import datetime, timezone

import feedparser
import requests

from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

TIMEOUT_SECONDS = 10        # FR-11
MAX_SUMMARY_CHARS = 300
HEADERS = {"User-Agent": "Briefly/1.0 (+https://github.com/irmakall/briefly)"}
TITLE_SIMILARITY = 0.85   # titles at least this similar count as the same story

TAG_PATTERN = re.compile(r"<[^>]+>")   # matches any HTML tag like <p> or <a href="...">


def _clean_summary(raw: str) -> str:
    """Turn an HTML summary into short plain text."""
    text = TAG_PATTERN.sub(" ", raw)       # remove HTML tags
    text = html.unescape(text)             # &amp; -> &, &#8217; -> ’
    text = " ".join(text.split())          # collapse whitespace
    if len(text) > MAX_SUMMARY_CHARS:
        text = text[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0] + "..."   # cut at a word boundary
    return text


def _parse_date(entry) -> str | None:
    """Return the entry's publish date as an ISO string in UTC, or None."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    # feedparser always gives the time in UTC as a time.struct_time
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()


def _entry_to_item(entry, source: str) -> dict | None:
    """Convert one feed entry to the common format. Returns None if it has no link."""
    link = entry.get("link")
    if not link:
        return None

    return {
        "title": (entry.get("title") or "").strip(),
        "url": link,
        "source": source,
        "published_at": _parse_date(entry),
        "summary": _clean_summary(entry.get("summary") or ""),
    }


def fetch_feed(name: str, url: str) -> dict:
    """Download one feed and return {"items": [...]} or {"error": "..."}. Never raises."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()   # turn 404/500 into exceptions
    except requests.Timeout:
        return {"error": f"{name}: timed out after {TIMEOUT_SECONDS} seconds."}
    except requests.RequestException as exc:
        return {"error": f"{name}: could not download feed ({type(exc).__name__})."}

    feed = feedparser.parse(response.content)

    # feedparser doesn't raise on broken XML; it sets feed.bozo instead.
    # A slightly broken feed may still have entries, so only fail if there are none.
    if feed.bozo and not feed.entries:
        return {"error": f"{name}: feed could not be parsed."}

    items = [_entry_to_item(entry, name) for entry in feed.entries]
    return {"items": [item for item in items if item is not None]}

def _normalize_url(url: str) -> str:
    """Reduce a URL to a comparable form: no query, no fragment, no trailing slash."""
    parts = urlsplit(url)

    # Keep scheme and path, lower-case the host, drop query (?...) and fragment (#...)
    normalized = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, "", ""))
    return normalized.rstrip("/")


def _normalize_title(title: str) -> str:
    """Lower-case a title and collapse its whitespace, for comparison."""
    return " ".join(title.lower().split())

def _is_similar(a: str, b: str) -> bool:
    """True if two normalized titles are close enough to be the same story."""
    val = SequenceMatcher(None, a, b).ratio()
    return val >= TITLE_SIMILARITY

def deduplicate(items: list[dict]) -> list[dict]:
    """Drop items with the same URL or a near-identical title. Keeps the first one seen (FR-29)."""
    seen_urls = set()
    kept_titles = []
    kept = []

    for item in items:
        url = _normalize_url(item["url"])
        title = _normalize_title(item["title"])

        if url in seen_urls:  # same URL → duplicate
            continue
        if any(_is_similar(title, t) for t in kept_titles):  # similar title → duplicate
            continue

        # new story: remember it and keep it
        seen_urls.add(url)
        kept_titles.append(title)
        kept.append(item)

    return kept


def fetch_all_feeds(feeds: list[dict]) -> dict:
    """Fetch every feed, merge the items and drop duplicates (FR-30).

    Returns {"items": [...]} plus an "errors" list if some feeds failed.
    One failing feed never stops the others.
    """
    items = []
    errors = []

    for feed_conf in feeds:
        feed_result = fetch_feed(feed_conf["name"], feed_conf["url"])
        if "error" in feed_result:
            errors.append(feed_result["error"])
        else:
            items.extend(feed_result["items"])

    result = {"items": deduplicate(items)}
    if errors:
        result["errors"] = errors
    return result


if __name__ == "__main__":
    # Quick manual test: python -m tools.feeds
    import json
    import config

    result = fetch_all_feeds(config.RSS_FEEDS)
    print(f"{len(result['items'])} unique items")
    print("errors:", result.get("errors", []))
    print(json.dumps(result["items"][:2], ensure_ascii=False, indent=2))
