from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from .config import SEARCH_KEYWORDS, SOURCES, SourceSpec
from .fetch import Fetcher
from .models import Listing
from .parser import parse_detail_description, parse_search_results
from .text import compact_url, extract_related_keywords, match_model, normalize_text

LOGGER = logging.getLogger(__name__)


class RadarScraper:
    def __init__(
        self,
        sources: Optional[list[SourceSpec]] = None,
        keywords: Optional[list[str]] = None,
        max_pages: int = 1,
        fetch_details: bool = True,
        strict_robots: bool = True,
        renderer: str = "requests",
    ) -> None:
        self.sources = sources or SOURCES
        self.keywords = keywords or SEARCH_KEYWORDS
        self.max_pages = max_pages
        self.fetch_details = fetch_details
        self.renderer = renderer
        self.fetcher = Fetcher(strict_robots=strict_robots)

    def run(self) -> list[Listing]:
        today = date.today()
        scrape_date = today.isoformat()
        scrape_week = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
        listings: list[Listing] = []

        for source in self.sources:
            for keyword in self.keywords:
                for page in range(1, self.max_pages + 1):
                    url = source.search_url(keyword, page)
                    LOGGER.info("Fetching %s | %s | page %s", source.source, keyword, page)
                    if self.renderer == "playwright":
                        result = self.fetcher.render(url, source.min_delay_seconds)
                    else:
                        result = self.fetcher.get(url, source.min_delay_seconds)
                    if result.error:
                        LOGGER.warning("Skipped %s: %s", url, result.error)
                        break

                    parsed = parse_search_results(result.text, source, keyword)
                    if not parsed and self.renderer == "auto":
                        LOGGER.info("No request-parsed listings; trying Playwright for %s", result.url)
                        rendered = self.fetcher.render(url, source.min_delay_seconds)
                        if rendered.error:
                            LOGGER.warning("Playwright fallback skipped %s: %s", url, rendered.error)
                        else:
                            result = rendered
                            parsed = parse_search_results(result.text, source, keyword)
                    LOGGER.info("Parsed %s listing candidates from %s", len(parsed), result.url)
                    if not parsed:
                        break

                    for item in parsed:
                        detail_text = ""
                        if self.fetch_details and item.url:
                            detail_result = self.fetcher.get(item.url, source.min_delay_seconds)
                            if not detail_result.error:
                                detail_text = parse_detail_description(detail_result.text)

                        combined_text = f"{item.title} {item.raw_text} {detail_text}"
                        matched_model = match_model(combined_text)
                        if not matched_model:
                            continue
                        related = extract_related_keywords(combined_text)
                        listing_url = compact_url(item.url)
                        title_normalized = normalize_text(item.title)
                        location_normalized = normalize_text(item.location)
                        dedupe_key = "|".join(
                            [
                                title_normalized,
                                str(item.price_numeric or ""),
                                location_normalized,
                            ]
                        )
                        listings.append(
                            Listing(
                                scrape_date=scrape_date,
                                scrape_week=scrape_week,
                                country=source.country,
                                source=source.source,
                                search_keyword=keyword,
                                matched_model=matched_model,
                                listing_title=item.title,
                                title_text_raw=item.raw_text,
                                description_text_raw=detail_text,
                                price=item.price,
                                currency=item.currency,
                                location=item.location,
                                posted_time=item.posted_time,
                                listing_url=listing_url,
                                related_keywords=";".join(related),
                                price_numeric=item.price_numeric,
                                title_normalized=title_normalized,
                                location_normalized=location_normalized,
                                dedupe_key_title_price_location=dedupe_key,
                            )
                        )
        return listings
