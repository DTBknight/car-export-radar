from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .aggregate import read_csv


def build_payload(input_dir: Path) -> dict:
    model_frequency = read_csv(input_dir / "model_frequency_by_market.csv")
    weekly_change = read_csv(input_dir / "model_frequency_change_weekly.csv")
    related_frequency = read_csv(input_dir / "related_keyword_frequency.csv")
    price_ranges = read_csv(input_dir / "price_range_by_model_market.csv")
    cleaned_sources = read_csv(input_dir / "cleaned_listings.csv")
    raw_sources = read_csv(input_dir / "raw_listings.csv")

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(input_dir),
            "row_counts": {
                "model_frequency": len(model_frequency),
                "weekly_change": len(weekly_change),
                "related_frequency": len(related_frequency),
                "price_ranges": len(price_ranges),
                "cleaned_sources": len(cleaned_sources),
                "raw_sources": len(raw_sources),
            },
        },
        "model_frequency": model_frequency,
        "weekly_change": weekly_change,
        "related_frequency": related_frequency,
        "price_ranges": price_ranges,
        "cleaned_sources": cleaned_sources[:500],
        "raw_sources": raw_sources[:500],
    }


def write_json(input_dir: Path, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(input_dir)
    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static site JSON from generated radar CSV files.")
    parser.add_argument("--input", default="output", help="Directory containing generated CSV outputs.")
    parser.add_argument("--out", default="data/latest.json", help="JSON file to write.")
    args = parser.parse_args()

    write_json(Path(args.input), Path(args.out))
    print(f"Wrote site data to {args.out}")


if __name__ == "__main__":
    main()
