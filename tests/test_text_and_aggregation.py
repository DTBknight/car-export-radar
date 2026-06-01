from pathlib import Path

from vehicle_frequency_radar.aggregate import dedupe_mentions, dedupe_rows, write_mention_outputs, write_outputs
from vehicle_frequency_radar.dashboard import generate_dashboard
from vehicle_frequency_radar.config import DiscussionSourceSpec
from vehicle_frequency_radar.mention_scraper import parse_discussion_results
from vehicle_frequency_radar.site import write_json
from vehicle_frequency_radar.source_loader import load_discussion_sources
from vehicle_frequency_radar.text import (
    extract_related_keywords,
    extract_trader_signal_keywords,
    match_model,
    parse_price,
)


def test_model_matching_is_alias_aware() -> None:
    assert match_model("MG 5 2025 automatique") == "MG5"
    assert match_model("Geely Livan X3 Pro full option") == "Livan X3 Pro"


def test_related_keyword_matching_is_accent_insensitive() -> None:
    related = extract_related_keywords("Chery Tiggo 4 Pro neuf dedouane sans dedouanement 00 km")
    assert "neuf" in related
    assert "dédouané" in related
    assert "sans dédouanement" in related
    assert "00km" in related


def test_trader_signal_matching_detects_procurement_context() -> None:
    signals = extract_trader_signal_keywords("MG5 disponible sur commande port Alger sans dedouanement")
    assert "disponible" in signals
    assert "sur commande" in signals
    assert "sans dédouanement" in signals


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


def test_dedupe_mentions_by_discussion_url() -> None:
    rows = [
        {"discussion_url": "https://x/1", "dedupe_key_text_url": "a"},
        {"discussion_url": "https://x/1", "dedupe_key_text_url": "a"},
        {"discussion_url": "", "dedupe_key_text_url": "b"},
    ]
    assert len(dedupe_mentions(rows)) == 2


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


def test_mention_outputs_are_created(tmp_path: Path) -> None:
    row = {
        "scrape_date": "2026-05-31",
        "scrape_week": "2026-W22",
        "country": "Algeria",
        "source": "Reddit r/algeria",
        "source_type": "reddit_search",
        "search_keyword": "MG5",
        "matched_model": "MG5",
        "mention_title": "MG5 import from China",
        "mention_text_raw": "MG5 available sur commande port Alger",
        "author_or_channel": "dealer",
        "published_time": "2026-05-31T00:00:00+00:00",
        "discussion_url": "https://example.com/post",
        "related_keywords": "import",
        "trader_signal_keywords": "sur commande;port alger",
        "title_normalized": "mg5 import from china",
        "dedupe_key_text_url": "https://example.com/post|mg5",
    }
    write_mention_outputs(tmp_path, [row], [row])
    assert (tmp_path / "raw_mentions.csv").exists()
    assert (tmp_path / "model_heat_by_market.csv").exists()
    assert (tmp_path / "trader_signal_frequency.csv").exists()


def test_dashboard_is_created_from_outputs(tmp_path: Path) -> None:
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
    generate_dashboard(tmp_path, tmp_path / "dashboard.html")
    html = (tmp_path / "dashboard.html").read_text(encoding="utf-8")
    assert "车辆车型频次雷达" in html
    assert "Dacia Duster" in html


def test_site_json_is_created_from_outputs(tmp_path: Path) -> None:
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
    write_json(tmp_path, tmp_path / "latest.json")
    payload = (tmp_path / "latest.json").read_text(encoding="utf-8")
    assert "model_frequency" in payload
    assert "Dacia Duster" in payload


def test_site_json_includes_discussion_outputs(tmp_path: Path) -> None:
    row = {
        "scrape_date": "2026-05-31",
        "scrape_week": "2026-W22",
        "country": "Algeria",
        "source": "Reddit r/algeria",
        "source_type": "reddit_search",
        "search_keyword": "MG5",
        "matched_model": "MG5",
        "mention_title": "MG5 import from China",
        "mention_text_raw": "MG5 available sur commande port Alger",
        "author_or_channel": "dealer",
        "published_time": "2026-05-31T00:00:00+00:00",
        "discussion_url": "https://example.com/post",
        "related_keywords": "import",
        "trader_signal_keywords": "sur commande;port alger",
        "title_normalized": "mg5 import from china",
        "dedupe_key_text_url": "https://example.com/post|mg5",
    }
    write_mention_outputs(tmp_path, [row], [row])
    write_json(tmp_path, tmp_path / "latest.json")
    payload = (tmp_path / "latest.json").read_text(encoding="utf-8")
    assert "model_heat" in payload
    assert "trader_frequency" in payload


def test_source_loader_reads_enabled_public_sources(tmp_path: Path) -> None:
    source_file = tmp_path / "sources.csv"
    source_file.write_text(
        "country,source,source_type,base_url,url_template,min_delay_seconds,enabled,api_key_env\n"
        "Algeria,Dealer,public_html,https://example.com,https://example.com/search?q={query}&page={page},5,true,\n",
        encoding="utf-8",
    )
    sources = load_discussion_sources(source_file)
    assert len(sources) == 1
    assert sources[0].search_url("MG 5", 2) == "https://example.com/search?q=MG+5&page=2"


def test_youtube_search_parser_extracts_video_mentions() -> None:
    source = DiscussionSourceSpec(
        country="Algeria",
        source="YouTube",
        source_type="youtube_search_api",
        base_url="https://www.youtube.com",
        search_url=lambda q, page: "",
    )
    rows = parse_discussion_results(
        """
        {
          "items": [{
            "id": {"videoId": "abc123"},
            "snippet": {
              "title": "MG5 disponible Alger",
              "description": "sur commande import chine",
              "channelTitle": "Dealer Channel",
              "publishedAt": "2026-06-01T00:00:00Z"
            }
          }]
        }
        """,
        source,
    )
    assert rows[0]["url"] == "https://www.youtube.com/watch?v=abc123"
    assert "sur commande" in rows[0]["text"]
