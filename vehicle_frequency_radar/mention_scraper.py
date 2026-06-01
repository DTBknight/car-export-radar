from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .config import DISCUSSION_SOURCES, SEARCH_KEYWORDS, DiscussionSourceSpec
from .fetch import Fetcher
from .models import Mention
from .text import (
    compact_url,
    extract_related_keywords,
    extract_trader_signal_keywords,
    match_model,
    normalize_text,
)

LOGGER = logging.getLogger(__name__)


class MentionScraper:
    def __init__(
        self,
        sources: Optional[list[DiscussionSourceSpec]] = None,
        keywords: Optional[list[str]] = None,
        max_pages: int = 1,
        strict_robots: bool = True,
    ) -> None:
        self.sources = sources or DISCUSSION_SOURCES
        self.keywords = keywords or SEARCH_KEYWORDS
        self.max_pages = max_pages
        self.fetcher = Fetcher(strict_robots=strict_robots)

    def run(self) -> list[Mention]:
        today = date.today()
        scrape_date = today.isoformat()
        scrape_week = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
        mentions: list[Mention] = []

        for source in self.sources:
            for keyword in self.keywords:
                for page in range(1, self.max_pages + 1):
                    url = source.search_url(keyword, page)
                    LOGGER.info("Fetching discussion source %s | %s", source.source, keyword)
                    result = self.fetcher.get(url, source.min_delay_seconds)
                    if result.error:
                        LOGGER.warning("Skipped %s: %s", url, result.error)
                        break

                    parsed = parse_discussion_results(result.text, source)
                    LOGGER.info("Parsed %s mention candidates from %s", len(parsed), result.url)
                    if not parsed:
                        break

                    for item in parsed:
                        combined = f"{item['title']} {item['text']}"
                        matched_model = match_model(combined)
                        if not matched_model:
                            continue

                        related = extract_related_keywords(combined)
                        trader_signals = extract_trader_signal_keywords(combined)
                        title_normalized = normalize_text(item["title"])
                        discussion_url = compact_url(item["url"])
                        text_key = normalize_text(combined)[:220]
                        mentions.append(
                            Mention(
                                scrape_date=scrape_date,
                                scrape_week=scrape_week,
                                country=source.country,
                                source=source.source,
                                source_type=source.source_type,
                                search_keyword=keyword,
                                matched_model=matched_model,
                                mention_title=item["title"],
                                mention_text_raw=item["text"],
                                author_or_channel=item["author"],
                                published_time=item["published_time"],
                                discussion_url=discussion_url,
                                related_keywords=";".join(related),
                                trader_signal_keywords=";".join(trader_signals),
                                title_normalized=title_normalized,
                                dedupe_key_text_url=f"{discussion_url}|{text_key}",
                            )
                        )
        return mentions


def parse_discussion_results(text: str, source: DiscussionSourceSpec) -> list[dict[str, str]]:
    if source.source_type == "reddit_search":
        return _parse_reddit_search(text, source.base_url)
    return _parse_public_html(text, source.base_url)


def _parse_reddit_search(text: str, base_url: str) -> list[dict[str, str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    rows: list[dict[str, str]] = []
    for child in payload.get("data", {}).get("children", []):
        data = child.get("data", {})
        title = _clean(data.get("title", ""))
        body = _clean(data.get("selftext", ""))
        permalink = str(data.get("permalink") or data.get("url") or "")
        created = data.get("created_utc")
        rows.append(
            {
                "title": title,
                "text": _clean(f"{title} {body}"),
                "author": str(data.get("author") or ""),
                "published_time": _utc_from_timestamp(created),
                "url": compact_url(urljoin(base_url, permalink)),
            }
        )
    return _unique(rows)


def _parse_public_html(text: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(text, "html.parser")
    rows: list[dict[str, str]] = []
    for node in soup.select("article, main, [class*='post'], [class*='card'], a[href]"):
        raw = _clean(node.get_text(" ", strip=True))
        if len(raw) < 30:
            continue
        anchor = node if node.name == "a" else node.select_one("a[href]")
        href = str(anchor.get("href") or "") if anchor else ""
        title = _clean(_first_heading(node) or raw[:140])
        rows.append(
            {
                "title": title,
                "text": raw,
                "author": "",
                "published_time": "",
                "url": compact_url(urljoin(base_url, href)),
            }
        )
    return _unique(rows)


def _first_heading(node) -> str:
    heading = node.select_one("h1, h2, h3")
    return heading.get_text(" ", strip=True) if heading else ""


def _utc_from_timestamp(value: object) -> str:
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _unique(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = row.get("url") or normalize_text(f"{row.get('title')} {row.get('text')[:120]}")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())
