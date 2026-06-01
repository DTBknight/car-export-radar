from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional, Union


@dataclass
class Listing:
    scrape_date: str
    scrape_week: str
    country: str
    source: str
    search_keyword: str
    matched_model: str
    listing_title: str
    title_text_raw: str
    description_text_raw: str
    price: str
    currency: str
    location: str
    posted_time: str
    listing_url: str
    related_keywords: str
    price_numeric: Optional[float] = None
    title_normalized: str = ""
    location_normalized: str = ""
    dedupe_key_title_price_location: str = ""

    def asdict(self) -> dict[str, Union[str, float, None]]:
        return asdict(self)


@dataclass
class Mention:
    scrape_date: str
    scrape_week: str
    country: str
    source: str
    source_type: str
    search_keyword: str
    matched_model: str
    mention_title: str
    mention_text_raw: str
    author_or_channel: str
    published_time: str
    discussion_url: str
    related_keywords: str
    trader_signal_keywords: str
    title_normalized: str = ""
    dedupe_key_text_url: str = ""

    def asdict(self) -> dict[str, str]:
        return asdict(self)
