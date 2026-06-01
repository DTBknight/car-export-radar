from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .aggregate import dedupe_mentions, dedupe_rows, read_csv, write_mention_outputs, write_outputs
from .config import (
    CLEANED_FIELDS,
    CLEANED_MENTION_FIELDS,
    DISCUSSION_SOURCES,
    RAW_FIELDS,
    RAW_MENTION_FIELDS,
    SEARCH_KEYWORDS,
    SOURCES,
)
from .dashboard import generate_dashboard
from .mention_scraper import MentionScraper
from .scraper import RadarScraper
from .source_loader import load_discussion_sources


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public vehicle model discussion heat or supply reference counts."
    )
    parser.add_argument(
        "--mode",
        choices=["mentions", "supply"],
        default="mentions",
        help="mentions collects discussion/procurement signals; supply collects vehicle listing references.",
    )
    parser.add_argument("--out", default="output", help="Output directory for CSV files.")
    parser.add_argument("--max-pages", type=int, default=1, help="Search result pages per keyword/source.")
    parser.add_argument(
        "--source",
        action="append",
        help="Limit to a source name. Can be passed multiple times, e.g. --source Avito.",
    )
    parser.add_argument(
        "--country",
        action="append",
        help="Limit to a country. Can be passed multiple times, e.g. --country Morocco.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        help="Limit to specific search keyword(s). Can be passed multiple times.",
    )
    parser.add_argument(
        "--discussion-source-file",
        default="config/discussion_sources.csv",
        help="Optional CSV of extra public discussion sources for --mode mentions.",
    )
    parser.add_argument(
        "--no-fetch-details",
        action="store_true",
        help="Only parse search result pages, without fetching listing detail pages.",
    )
    parser.add_argument(
        "--non-strict-robots",
        action="store_true",
        help="Continue if robots.txt cannot be fetched. Explicit disallow rules are still respected.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Merge this run with existing output CSVs before deduping and aggregating.",
    )
    parser.add_argument(
        "--renderer",
        choices=["requests", "auto", "playwright"],
        default="requests",
        help="Use requests, Playwright, or Playwright only after requests parses no listings.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate a static HTML dashboard after writing CSV outputs.",
    )
    parser.add_argument(
        "--dashboard-file",
        default="dashboard.html",
        help="Dashboard filename inside the output directory when --dashboard is used.",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    sources = DISCUSSION_SOURCES if args.mode == "mentions" else SOURCES
    if args.mode == "mentions" and args.discussion_source_file:
        extra_sources = load_discussion_sources(Path(args.discussion_source_file))
        sources = [*sources, *extra_sources]
    if args.source:
        wanted = {value.lower() for value in args.source}
        sources = [source for source in sources if source.source.lower() in wanted]
    if args.country:
        wanted_countries = {value.lower() for value in args.country}
        sources = [source for source in sources if source.country.lower() in wanted_countries]
    if args.mode == "mentions" and not sources:
        logging.warning(
            "No discussion sources are enabled. Check --source filters, config/discussion_sources.csv, and API key secrets."
        )

    keywords = args.keyword or SEARCH_KEYWORDS
    out_dir = Path(args.out)
    if args.mode == "mentions":
        scraper = MentionScraper(
            sources=sources,
            keywords=keywords,
            max_pages=args.max_pages,
            strict_robots=not args.non_strict_robots,
        )
        mentions = scraper.run()
        new_cleaned = [mention.asdict() for mention in mentions]
        new_raw = [{field: row.get(field, "") for field in RAW_MENTION_FIELDS} for row in new_cleaned]

        if args.append:
            raw_rows = read_csv(out_dir / "raw_mentions.csv") + new_raw
            cleaned_rows = read_csv(out_dir / "cleaned_mentions.csv") + new_cleaned
        else:
            raw_rows = new_raw
            cleaned_rows = new_cleaned

        cleaned_rows = dedupe_mentions(cleaned_rows)
        raw_by_url = {row.get("discussion_url", ""): row for row in raw_rows if row.get("discussion_url")}
        raw_rows = [
            {field: raw_by_url.get(row.get("discussion_url", ""), row).get(field, "") for field in RAW_MENTION_FIELDS}
            for row in cleaned_rows
        ]
        cleaned_rows = [{field: row.get(field, "") for field in CLEANED_MENTION_FIELDS} for row in cleaned_rows]
        write_mention_outputs(out_dir, raw_rows, cleaned_rows)
        print(f"Wrote {len(cleaned_rows)} deduped public mentions to {out_dir}")
    else:
        scraper = RadarScraper(
            sources=sources,
            keywords=keywords,
            max_pages=args.max_pages,
            fetch_details=not args.no_fetch_details,
            strict_robots=not args.non_strict_robots,
            renderer=args.renderer,
        )
        listings = scraper.run()
        new_cleaned = [listing.asdict() for listing in listings]
        new_raw = [{field: row.get(field, "") for field in RAW_FIELDS} for row in new_cleaned]

        if args.append:
            raw_rows = read_csv(out_dir / "raw_listings.csv") + new_raw
            cleaned_rows = read_csv(out_dir / "cleaned_listings.csv") + new_cleaned
        else:
            raw_rows = new_raw
            cleaned_rows = new_cleaned

        cleaned_rows = dedupe_rows(cleaned_rows)
        raw_by_url = {row.get("listing_url", ""): row for row in raw_rows if row.get("listing_url")}
        raw_rows = [
            {field: raw_by_url.get(row.get("listing_url", ""), row).get(field, "") for field in RAW_FIELDS}
            for row in cleaned_rows
        ]
        cleaned_rows = [{field: row.get(field, "") for field in CLEANED_FIELDS} for row in cleaned_rows]
        write_outputs(out_dir, raw_rows, cleaned_rows)
        print(f"Wrote {len(cleaned_rows)} deduped supply references to {out_dir}")

    if args.dashboard:
        generate_dashboard(out_dir, out_dir / args.dashboard_file)


if __name__ == "__main__":
    main()
