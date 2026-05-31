from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import SourceSpec
from .text import match_model, parse_price


@dataclass
class ParsedListing:
    title: str
    raw_text: str
    price: str
    price_numeric: Optional[float]
    currency: str
    location: str
    posted_time: str
    url: str


def parse_search_results(html: str, source: SourceSpec, search_keyword: str) -> list[ParsedListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = _parse_json_ld(soup, source.base_url)
    listings.extend(_parse_cards(soup, source, search_keyword))
    return _unique_by_url_or_title(listings)


def parse_detail_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in (
        "meta[property='og:description']",
        "meta[name='description']",
        "[class*='description']",
        "[class*='Description']",
        "article",
        "main",
    ):
        node = soup.select_one(selector)
        if not node:
            continue
        if node.name == "meta":
            content = node.get("content", "")
            if content:
                return _clean_text(content)
        text = _clean_text(node.get_text(" ", strip=True))
        if len(text) > 40:
            return text
    return ""


def _parse_json_ld(soup: BeautifulSoup, base_url: str) -> list[ParsedListing]:
    listings: list[ParsedListing] = []
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _walk_json_objects(payload):
            listing = _json_listing(item, base_url)
            if listing:
                listings.append(listing)
    return listings


def _json_listing(item: dict, base_url: str) -> Optional[ParsedListing]:
    item_type = item.get("@type")
    if isinstance(item_type, list):
        item_types = {str(value).lower() for value in item_type}
    else:
        item_types = {str(item_type).lower()}
    if not item_types.intersection({"product", "vehicle", "car", "listitem", "offer"}):
        return None

    data = item.get("item") if isinstance(item.get("item"), dict) else item
    title = str(data.get("name") or data.get("title") or "").strip()
    url = str(data.get("url") or item.get("url") or "").strip()
    if not title or not url:
        return None

    offers = data.get("offers") or item.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price_value = str(offers.get("price") or item.get("price") or "").strip()
    currency = str(offers.get("priceCurrency") or item.get("priceCurrency") or "").strip()
    raw_price, price_numeric, parsed_currency = parse_price(f"{price_value} {currency}")

    return ParsedListing(
        title=title,
        raw_text=_clean_text(" ".join(str(value) for value in data.values() if isinstance(value, str))),
        price=raw_price,
        price_numeric=price_numeric,
        currency=currency or parsed_currency,
        location="",
        posted_time=str(data.get("datePosted") or item.get("datePosted") or ""),
        url=urljoin(base_url, url),
    )


def _walk_json_objects(payload: object) -> Iterable[dict]:
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _walk_json_objects(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _walk_json_objects(value)


def _parse_cards(
    soup: BeautifulSoup,
    source: SourceSpec,
    search_keyword: str,
) -> list[ParsedListing]:
    cards: list[Tag] = []
    for selector in source.result_selectors:
        cards.extend(tag for tag in soup.select(selector) if isinstance(tag, Tag))

    if not cards:
        cards = _cards_from_anchors(soup)

    listings: list[ParsedListing] = []
    for card in cards:
        raw_text = _clean_text(card.get_text(" ", strip=True))
        if len(raw_text) < 10:
            continue

        link = _best_link(card)
        if not link:
            continue

        title = _first_selector_text(card, source.title_selectors) or _link_text(card) or raw_text[:140]
        title = _clean_text(title)
        searchable_text = f"{title} {raw_text} {search_keyword}"
        if not match_model(searchable_text):
            continue

        price_text = _first_selector_text(card, source.price_selectors) or _price_like(raw_text)
        raw_price, price_numeric, currency = parse_price(price_text)

        listings.append(
            ParsedListing(
                title=title,
                raw_text=raw_text,
                price=raw_price,
                price_numeric=price_numeric,
                currency=currency,
                location=_first_selector_text(card, source.location_selectors),
                posted_time=_first_selector_text(card, source.time_selectors),
                url=urljoin(source.base_url, link),
            )
        )
    return listings


def _cards_from_anchors(soup: BeautifulSoup) -> list[Tag]:
    cards: list[Tag] = []
    seen: set[int] = set()
    for anchor in soup.select("a[href]"):
        text = _clean_text(anchor.get_text(" ", strip=True))
        href = anchor.get("href", "")
        if len(text) < 6 or href.startswith("#"):
            continue
        card = anchor
        for _ in range(4):
            if card.parent and isinstance(card.parent, Tag):
                card = card.parent
                if len(_clean_text(card.get_text(" ", strip=True))) > 30:
                    break
        identity = id(card)
        if identity not in seen:
            seen.add(identity)
            cards.append(card)
    return cards


def _best_link(card: Tag) -> str:
    if card.name == "a" and card.get("href"):
        return str(card.get("href"))
    for anchor in card.select("a[href]"):
        href = str(anchor.get("href") or "")
        if href and not href.startswith("#") and not href.startswith("javascript:"):
            return href
    return ""


def _link_text(card: Tag) -> str:
    anchor = card if card.name == "a" else card.select_one("a[href]")
    if not anchor:
        return ""
    return _clean_text(anchor.get_text(" ", strip=True))


def _first_selector_text(card: Tag, selectors: Iterable[str]) -> str:
    for selector in selectors:
        node = card.select_one(selector)
        if node:
            text = _clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _price_like(text: str) -> str:
    patterns = (
        r"\d[\d\s.,]{2,}\s*(?:DA|DZD|دج|LYD|LD|MAD|DH|DHS|درهم)\b",
        r"(?:DA|DZD|دج|LYD|LD|MAD|DH|DHS|درهم)\s*\d[\d\s.,]{2,}",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _unique_by_url_or_title(listings: list[ParsedListing]) -> list[ParsedListing]:
    unique: list[ParsedListing] = []
    seen: set[str] = set()
    for listing in listings:
        key = listing.url or f"{listing.title}|{listing.price}|{listing.location}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(listing)
    return unique


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = re.sub(r"[\u200e\u200f\xa0]", " ", value)
    return re.sub(r"\s+", " ", value).strip()
