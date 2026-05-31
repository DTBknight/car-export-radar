from pathlib import Path

from vehicle_frequency_radar.aggregate import dedupe_rows, write_outputs
from vehicle_frequency_radar.text import extract_related_keywords, match_model, parse_price


def test_model_matching_is_alias_aware() -> None:
    assert match_model("MG 5 2025 automatique") == "MG5"
    assert match_model("Geely Livan X3 Pro full option") == "Livan X3 Pro"


def test_related_keyword_matching_is_accent_insensitive() -> None:
    related = extract_related_keywords("Chery Tiggo 4 Pro neuf dedouane sans dedouanement 00 km")
    assert "neuf" in related
    assert "dédouané" in related
    assert "sans dédouanement" in related
    assert "00km" in related


def test_price_parser_extracts_currency_and_number() -> None:
    raw, numeric, currency = parse_price("280 000 DH")
    assert raw == "280 000 DH"
    assert numeric == 280000
    assert currency == "MAD"


def test_dedupe_by_url_and_composite_key() -> None:
    rows = [
        {"listing_url": "https://x/1", "dedupe_key_title_price_location": "a|1|x"},
        {"listing_url": "https://x/1", "dedupe_key_title_price_location": "a|1|x"},
        {"listing_url": "https://x/2", "dedupe_key_title_price_location": "a|1|x"},
        {"listing_url": "", "dedupe_key_title_price_location": "b|2|y"},
    ]
    assert len(dedupe_rows(rows)) == 2


def test_outputs_are_created(tmp_path: Path) -> None:
    row = {
        "scrape_date": "2026-05-31",
        "scrape_week": "2026-W22",
        "country": "Morocco",
        "source": "Avito",
        "search_keyword": "Dacia Duster",
        "matched_model": "Dacia Duster",
        "listing_title": "Dacia Duster 2025",
        "title_text_raw": "Dacia Duster 2025 220 000 DH",
        "description_text_raw": "neuf",
        "price": "220 000 DH",
        "currency": "MAD",
        "location": "Casablanca",
        "posted_time": "today",
        "listing_url": "https://example.com/1",
        "related_keywords": "2025;neuf",
        "price_numeric": 220000,
        "title_normalized": "dacia duster 2025",
        "location_normalized": "casablanca",
        "dedupe_key_title_price_location": "dacia duster 2025|220000|casablanca",
    }
    write_outputs(tmp_path, [row], [row])
    assert (tmp_path / "raw_listings.csv").exists()
    assert (tmp_path / "model_frequency_by_market.csv").exists()
    assert (tmp_path / "price_range_by_model_market.csv").exists()
