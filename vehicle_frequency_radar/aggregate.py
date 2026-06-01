from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Iterable

from .config import CLEANED_FIELDS, CLEANED_MENTION_FIELDS, RAW_FIELDS, RAW_MENTION_FIELDS


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def dedupe_rows(rows: Iterable[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    by_composite: dict[str, dict] = {}
    for row in rows:
        url = str(row.get("listing_url") or "").strip()
        composite = str(row.get("dedupe_key_title_price_location") or "").strip()
        if url and url in by_url:
            continue
        if composite and composite in by_composite:
            continue
        if url:
            by_url[url] = row
        if composite:
            by_composite[composite] = row
    return list(by_url.values()) + [
        row for key, row in by_composite.items() if not row.get("listing_url")
    ]


def dedupe_mentions(rows: Iterable[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    by_text: dict[str, dict] = {}
    for row in rows:
        url = str(row.get("discussion_url") or "").strip()
        composite = str(row.get("dedupe_key_text_url") or "").strip()
        if url and url in by_url:
            continue
        if composite and composite in by_text:
            continue
        if url:
            by_url[url] = row
        if composite:
            by_text[composite] = row
    return list(by_url.values()) + [
        row for row in by_text.values() if not row.get("discussion_url")
    ]


def model_frequency_by_market(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str]] = Counter()
    urls: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    keywords: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        key = (row["country"], row["source"], row["matched_model"])
        counts[key] += 1
        if row.get("listing_url"):
            urls[key].add(row["listing_url"])
        if row.get("search_keyword"):
            keywords[key].add(row["search_keyword"])
    return [
        {
            "country": country,
            "source": source,
            "matched_model": model,
            "listing_count": count,
            "unique_url_count": len(urls[(country, source, model)]),
            "search_keywords": "; ".join(sorted(keywords[(country, source, model)])),
        }
        for (country, source, model), count in sorted(counts.items())
    ]


def model_frequency_change_weekly(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        counts[(row["scrape_week"], row["country"], row["source"], row["matched_model"])] += 1

    keys_by_series: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    for week, country, source, model in counts:
        keys_by_series[(country, source, model)].append(week)

    output: list[dict] = []
    for (country, source, model), weeks in sorted(keys_by_series.items()):
        previous_count = 0
        for week in sorted(set(weeks)):
            count = counts[(week, country, source, model)]
            absolute_change = count - previous_count
            pct_change = "" if previous_count == 0 else round((absolute_change / previous_count) * 100, 2)
            output.append(
                {
                    "scrape_week": week,
                    "country": country,
                    "source": source,
                    "matched_model": model,
                    "listing_count": count,
                    "previous_week_count": previous_count,
                    "absolute_change": absolute_change,
                    "pct_change": pct_change,
                }
            )
            previous_count = count
    return output


def related_keyword_frequency(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        related = str(row.get("related_keywords") or "")
        for keyword in [item.strip() for item in related.split(";") if item.strip()]:
            counts[(row["country"], row["source"], row["matched_model"], keyword)] += 1
    return [
        {
            "country": country,
            "source": source,
            "matched_model": model,
            "related_keyword": keyword,
            "listing_count": count,
        }
        for (country, source, model, keyword), count in sorted(counts.items())
    ]


def price_range_by_model_market(rows: Iterable[dict]) -> list[dict]:
    values: defaultdict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        raw = row.get("price_numeric")
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        key = (
            row["country"],
            row["source"],
            row["matched_model"],
            str(row.get("currency") or ""),
        )
        values[key].append(price)

    output: list[dict] = []
    for (country, source, model, currency), prices in sorted(values.items()):
        prices.sort()
        output.append(
            {
                "country": country,
                "source": source,
                "matched_model": model,
                "currency": currency,
                "listing_count_with_price": len(prices),
                "min_price": prices[0],
                "median_price": median(prices),
                "max_price": prices[-1],
            }
        )
    return output


def model_heat_by_market(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str]] = Counter()
    urls: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    keywords: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    trader_counts: Counter[tuple[str, str, str]] = Counter()
    latest_seen: dict[tuple[str, str, str], str] = {}
    for row in rows:
        key = (row["country"], row["source"], row["matched_model"])
        counts[key] += 1
        if row.get("discussion_url"):
            urls[key].add(row["discussion_url"])
        if row.get("search_keyword"):
            keywords[key].add(row["search_keyword"])
        if row.get("trader_signal_keywords"):
            trader_counts[key] += 1
        published = str(row.get("published_time") or row.get("scrape_date") or "")
        latest_seen[key] = max(latest_seen.get(key, ""), published)

    return [
        {
            "country": country,
            "source": source,
            "matched_model": model,
            "mention_count": count,
            "trader_signal_count": trader_counts[(country, source, model)],
            "unique_url_count": len(urls[(country, source, model)]),
            "latest_seen": latest_seen.get((country, source, model), ""),
            "search_keywords": "; ".join(sorted(keywords[(country, source, model)])),
        }
        for (country, source, model), count in sorted(counts.items())
    ]


def discussion_heat_change_weekly(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        counts[(row["scrape_week"], row["country"], row["source"], row["matched_model"])] += 1

    keys_by_series: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    for week, country, source, model in counts:
        keys_by_series[(country, source, model)].append(week)

    output: list[dict] = []
    for (country, source, model), weeks in sorted(keys_by_series.items()):
        previous_count = 0
        for week in sorted(set(weeks)):
            count = counts[(week, country, source, model)]
            absolute_change = count - previous_count
            pct_change = "" if previous_count == 0 else round((absolute_change / previous_count) * 100, 2)
            output.append(
                {
                    "scrape_week": week,
                    "country": country,
                    "source": source,
                    "matched_model": model,
                    "mention_count": count,
                    "previous_week_count": previous_count,
                    "absolute_change": absolute_change,
                    "pct_change": pct_change,
                }
            )
            previous_count = count
    return output


def trader_signal_frequency(rows: Iterable[dict]) -> list[dict]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        signals = str(row.get("trader_signal_keywords") or "")
        for keyword in [item.strip() for item in signals.split(";") if item.strip()]:
            counts[(row["country"], row["source"], row["matched_model"], keyword)] += 1
    return [
        {
            "country": country,
            "source": source,
            "matched_model": model,
            "trader_signal_keyword": keyword,
            "mention_count": count,
        }
        for (country, source, model, keyword), count in sorted(counts.items())
    ]


def source_coverage(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    counts: Counter[tuple[str, str, str]] = Counter()
    urls: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    models: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        key = (row["country"], row["source"], str(row.get("source_type") or ""))
        counts[key] += 1
        if row.get("discussion_url"):
            urls[key].add(row["discussion_url"])
        if row.get("matched_model"):
            models[key].add(row["matched_model"])
    return [
        {
            "country": country,
            "source": source,
            "source_type": source_type,
            "mention_count": count,
            "unique_url_count": len(urls[(country, source, source_type)]),
            "matched_model_count": len(models[(country, source, source_type)]),
        }
        for (country, source, source_type), count in sorted(counts.items())
    ]


def evidence_samples(rows: Iterable[dict], limit_per_model: int = 3) -> list[dict]:
    grouped: defaultdict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["country"], row["source"], row["matched_model"])].append(row)
    output: list[dict] = []
    for (country, source, model), group in sorted(grouped.items()):
        group.sort(key=lambda row: str(row.get("published_time") or row.get("scrape_date") or ""), reverse=True)
        for row in group[:limit_per_model]:
            output.append(
                {
                    "country": country,
                    "source": source,
                    "matched_model": model,
                    "mention_title": row.get("mention_title", ""),
                    "published_time": row.get("published_time", ""),
                    "discussion_url": row.get("discussion_url", ""),
                    "trader_signal_keywords": row.get("trader_signal_keywords", ""),
                }
            )
    return output


def write_outputs(out_dir: Path, raw_rows: list[dict], cleaned_rows: list[dict]) -> None:
    write_csv(out_dir / "raw_listings.csv", raw_rows, RAW_FIELDS)
    write_csv(out_dir / "cleaned_listings.csv", cleaned_rows, CLEANED_FIELDS)
    write_csv(
        out_dir / "model_frequency_by_market.csv",
        model_frequency_by_market(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "listing_count",
            "unique_url_count",
            "search_keywords",
        ],
    )
    write_csv(
        out_dir / "model_frequency_change_weekly.csv",
        model_frequency_change_weekly(cleaned_rows),
        [
            "scrape_week",
            "country",
            "source",
            "matched_model",
            "listing_count",
            "previous_week_count",
            "absolute_change",
            "pct_change",
        ],
    )
    write_csv(
        out_dir / "related_keyword_frequency.csv",
        related_keyword_frequency(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "related_keyword",
            "listing_count",
        ],
    )
    write_csv(
        out_dir / "price_range_by_model_market.csv",
        price_range_by_model_market(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "currency",
            "listing_count_with_price",
            "min_price",
            "median_price",
            "max_price",
        ],
    )


def write_mention_outputs(out_dir: Path, raw_rows: list[dict], cleaned_rows: list[dict]) -> None:
    write_csv(out_dir / "raw_mentions.csv", raw_rows, RAW_MENTION_FIELDS)
    write_csv(out_dir / "cleaned_mentions.csv", cleaned_rows, CLEANED_MENTION_FIELDS)
    write_csv(
        out_dir / "model_heat_by_market.csv",
        model_heat_by_market(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "mention_count",
            "trader_signal_count",
            "unique_url_count",
            "latest_seen",
            "search_keywords",
        ],
    )
    write_csv(
        out_dir / "discussion_heat_change_weekly.csv",
        discussion_heat_change_weekly(cleaned_rows),
        [
            "scrape_week",
            "country",
            "source",
            "matched_model",
            "mention_count",
            "previous_week_count",
            "absolute_change",
            "pct_change",
        ],
    )
    write_csv(
        out_dir / "trader_signal_frequency.csv",
        trader_signal_frequency(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "trader_signal_keyword",
            "mention_count",
        ],
    )
    write_csv(
        out_dir / "source_coverage.csv",
        source_coverage(cleaned_rows),
        [
            "country",
            "source",
            "source_type",
            "mention_count",
            "unique_url_count",
            "matched_model_count",
        ],
    )
    write_csv(
        out_dir / "evidence_samples.csv",
        evidence_samples(cleaned_rows),
        [
            "country",
            "source",
            "matched_model",
            "mention_title",
            "published_time",
            "discussion_url",
            "trader_signal_keywords",
        ],
    )
