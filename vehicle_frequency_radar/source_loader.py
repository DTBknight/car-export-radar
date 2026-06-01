from __future__ import annotations

import csv
import os
from pathlib import Path
from urllib.parse import quote_plus

from .config import DiscussionSourceSpec


def load_discussion_sources(path: Path) -> list[DiscussionSourceSpec]:
    if not path.exists():
        return []

    sources: list[DiscussionSourceSpec] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(row for row in handle if not row.lstrip().startswith("#"))
        for row in reader:
            if str(row.get("enabled", "")).strip().lower() not in {"1", "true", "yes", "y"}:
                continue
            template = str(row.get("url_template") or "").strip()
            if not template:
                continue
            api_key_env = str(row.get("api_key_env") or "").strip()
            api_key = os.environ.get(api_key_env, "") if api_key_env else ""
            if "{api_key}" in template and not api_key:
                continue
            sources.append(
                DiscussionSourceSpec(
                    country=str(row.get("country") or "").strip(),
                    source=str(row.get("source") or "").strip(),
                    source_type=str(row.get("source_type") or "public_html").strip(),
                    base_url=str(row.get("base_url") or "").strip(),
                    search_url=_template_url(template, api_key),
                    min_delay_seconds=_float_or_default(row.get("min_delay_seconds"), 4.0),
                )
            )
    return sources


def _template_url(template: str, api_key: str):
    def search_url(query: str, page: int) -> str:
        return template.format(
            query=quote_plus(query),
            page=page,
            api_key=api_key,
        )

    return search_url


def _float_or_default(value: object, default: float) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return default
