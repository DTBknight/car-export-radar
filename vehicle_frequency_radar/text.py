from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Optional

from .config import RELATED_KEYWORDS, TARGET_MODEL_ALIASES, TRADER_SIGNAL_KEYWORDS


CURRENCY_PATTERNS = {
    "DZD": re.compile(r"\b(?:DA|DZD|دج)\b", re.IGNORECASE),
    "LYD": re.compile(r"\b(?:LYD|LD|ل\.د|دينار)\b", re.IGNORECASE),
    "MAD": re.compile(r"\b(?:MAD|DH|DHS|درهم)\b", re.IGNORECASE),
}


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[\u200e\u200f\xa0]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact_url(url: str) -> str:
    return re.sub(r"([?&])(utm_[^=&]+|fbclid|gclid)=[^&]+&?", r"\1", url).rstrip("?&")


def _alias_pattern(alias: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in normalize_text(alias).split()]
    if not parts:
        return re.compile(r"$^")
    body = r"[\s\-_/]*".join(parts)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


@lru_cache(maxsize=1)
def model_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for canonical, aliases in TARGET_MODEL_ALIASES.items():
        for alias in aliases:
            patterns.append((canonical, _alias_pattern(alias)))
    patterns.sort(key=lambda item: len(item[1].pattern), reverse=True)
    return patterns


def match_model(text: str) -> str:
    normalized = normalize_text(text)
    for canonical, pattern in model_patterns():
        if pattern.search(normalized):
            return canonical
    return ""


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    normalized = normalize_text(keyword)
    if keyword == "00km":
        return re.compile(r"(?<![a-z0-9])0+\s*km(?![a-z0-9])", re.IGNORECASE)
    parts = [re.escape(part) for part in normalized.split()]
    body = r"[\s\-_/]*".join(parts)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


@lru_cache(maxsize=1)
def related_keyword_patterns() -> list[tuple[str, re.Pattern[str]]]:
    return [(keyword, _keyword_pattern(keyword)) for keyword in RELATED_KEYWORDS]


def extract_related_keywords(text: str) -> list[str]:
    normalized = normalize_text(text)
    found = [
        keyword
        for keyword, pattern in related_keyword_patterns()
        if pattern.search(normalized)
    ]
    return found


@lru_cache(maxsize=1)
def trader_signal_patterns() -> list[tuple[str, re.Pattern[str]]]:
    return [(keyword, _keyword_pattern(keyword)) for keyword in TRADER_SIGNAL_KEYWORDS]


def extract_trader_signal_keywords(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        keyword
        for keyword, pattern in trader_signal_patterns()
        if pattern.search(normalized)
    ]


def parse_price(value: Optional[str]) -> tuple[str, Optional[float], str]:
    raw = (value or "").strip()
    if not raw:
        return "", None, ""

    currency = ""
    for code, pattern in CURRENCY_PATTERNS.items():
        if pattern.search(raw):
            currency = code
            break

    match = re.search(r"(\d[\d\s.,]*)", raw)
    if not match:
        return raw, None, currency

    numeric_text = match.group(1)
    numeric_text = numeric_text.replace(" ", "").replace("\xa0", "")
    if numeric_text.count(",") == 1 and numeric_text.count(".") == 0:
        numeric_text = numeric_text.replace(",", ".")
    numeric_text = re.sub(r"(?<=\d)[,.](?=\d{3}\b)", "", numeric_text)
    try:
        price_numeric = float(numeric_text)
    except ValueError:
        price_numeric = None
    return raw, price_numeric, currency
