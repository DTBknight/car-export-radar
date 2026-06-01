from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote_plus


USER_AGENT = (
    "VehicleFrequencyRadarMVP/0.1 "
    "(public listing frequency research; contact: configure-in-readme)"
)

RAW_FIELDS = [
    "scrape_date",
    "scrape_week",
    "country",
    "source",
    "search_keyword",
    "matched_model",
    "listing_title",
    "title_text_raw",
    "description_text_raw",
    "price",
    "currency",
    "location",
    "posted_time",
    "listing_url",
    "related_keywords",
]

CLEANED_FIELDS = RAW_FIELDS + [
    "price_numeric",
    "title_normalized",
    "location_normalized",
    "dedupe_key_title_price_location",
]

RAW_MENTION_FIELDS = [
    "scrape_date",
    "scrape_week",
    "country",
    "source",
    "source_type",
    "search_keyword",
    "matched_model",
    "mention_title",
    "mention_text_raw",
    "author_or_channel",
    "published_time",
    "discussion_url",
    "related_keywords",
    "trader_signal_keywords",
]

CLEANED_MENTION_FIELDS = RAW_MENTION_FIELDS + [
    "title_normalized",
    "dedupe_key_text_url",
]

TARGET_MODEL_ALIASES: dict[str, list[str]] = {
    "MG5": ["MG5", "MG 5"],
    "Livan X3 Pro": ["Livan X3 Pro", "Geely Livan X3 Pro"],
    "Geely Coolray": ["Geely Coolray"],
    "Geely GX3 Pro": ["Geely GX3 Pro"],
    "GAC GS3": ["GAC GS3"],
    "Volkswagen Tharu": ["Volkswagen Tharu"],
    "Kia KX1": ["Kia KX1"],
    "Kaiyi X3 Pro": ["Kaiyi X3 Pro"],
    "Jetour X70": ["Jetour X70"],
    "Jetour Dashing": ["Jetour Dashing"],
    "Chery Tiggo 2 Pro": ["Chery Tiggo 2 Pro"],
    "Chery Tiggo 4 Pro": ["Chery Tiggo 4 Pro"],
    "Changan CS35": ["Changan CS35"],
    "Changan X5 Plus": ["Changan X5 Plus"],
    "Jetta VS5": ["Jetta VS5"],
    "Jetta VA3": ["Jetta VA3"],
    "MG ZS": ["MG ZS"],
    "Dacia Logan": ["Dacia Logan"],
    "Dacia Duster": ["Dacia Duster"],
    "Fiat Doblo": ["Fiat Doblo"],
    "Suzuki Dzire": ["Suzuki Dzire"],
    "Hyundai Accent": ["Hyundai Accent"],
}

SEARCH_KEYWORDS = [
    "MG5",
    "MG 5",
    "Livan X3 Pro",
    "Geely Livan X3 Pro",
    "Geely Coolray",
    "Geely GX3 Pro",
    "GAC GS3",
    "Volkswagen Tharu",
    "Kia KX1",
    "Kaiyi X3 Pro",
    "Jetour X70",
    "Jetour Dashing",
    "Chery Tiggo 2 Pro",
    "Chery Tiggo 4 Pro",
    "Changan CS35",
    "Changan X5 Plus",
    "Jetta VS5",
    "Jetta VA3",
    "MG ZS",
    "Dacia Logan",
    "Dacia Duster",
    "Fiat Doblo",
    "Suzuki Dzire",
    "Hyundai Accent",
]

RELATED_KEYWORDS = [
    "2025",
    "2026",
    "automatic",
    "automatique",
    "auto",
    "manual",
    "manuel",
    "full option",
    "toutes options",
    "luxury",
    "flagship",
    "battle",
    "00km",
    "new",
    "neuf",
    "disponible",
    "arrivage",
    "import",
    "chine",
    "dédouané",
    "sans dédouanement",
]

TRADER_SIGNAL_KEYWORDS = [
    "sur commande",
    "commande",
    "arrivage",
    "disponible",
    "stock",
    "en stock",
    "import",
    "importation",
    "chine",
    "china",
    "dédouané",
    "sans dédouanement",
    "port d'alger",
    "port alger",
    "prix jusqu'au port",
    "whatsapp",
    "showroom",
    "concessionnaire",
    "dealer",
    "grossiste",
    "lot",
    "batch",
    "purchase",
    "procurement",
    "order",
    "new arrival",
    "available",
]


@dataclass(frozen=True)
class SourceSpec:
    country: str
    source: str
    base_url: str
    search_url: Callable[[str, int], str]
    min_delay_seconds: float = 3.0
    result_selectors: tuple[str, ...] = field(default_factory=tuple)
    title_selectors: tuple[str, ...] = field(default_factory=tuple)
    price_selectors: tuple[str, ...] = field(default_factory=tuple)
    location_selectors: tuple[str, ...] = field(default_factory=tuple)
    time_selectors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DiscussionSourceSpec:
    country: str
    source: str
    source_type: str
    base_url: str
    search_url: Callable[[str, int], str]
    min_delay_seconds: float = 4.0


SOURCES = [
    SourceSpec(
        country="Algeria",
        source="Ouedkniss",
        base_url="https://www.ouedkniss.com",
        search_url=lambda q, page: (
            "https://www.ouedkniss.com/automobiles/2"
            f"?keywords={quote_plus(q)}&page={page}&lang=fr"
        ),
        result_selectors=("article", "[data-testid*='annonce']", ".annonce", ".card"),
        title_selectors=("h1", "h2", "h3", "[class*='title']", "[class*='Title']"),
        price_selectors=("[class*='price']", "[class*='Price']", "[class*='prix']"),
        location_selectors=("[class*='location']", "[class*='wilaya']", "[class*='adresse']"),
        time_selectors=("time", "[class*='date']", "[class*='time']"),
    ),
    SourceSpec(
        country="Libya",
        source="OpenSooq",
        base_url="https://ly.opensooq.com",
        search_url=lambda q, page: (
            "https://ly.opensooq.com/en/find"
            f"?term={quote_plus(q)}&page={page}"
        ),
        result_selectors=("article", "[data-testid*='post']", ".post", ".rectLi"),
        title_selectors=("h1", "h2", "h3", "[class*='title']", "[class*='Title']"),
        price_selectors=("[class*='price']", "[class*='Price']"),
        location_selectors=("[class*='location']", "[class*='city']", "[class*='area']"),
        time_selectors=("time", "[class*='date']", "[class*='time']"),
    ),
    SourceSpec(
        country="Morocco",
        source="Avito",
        base_url="https://www.avito.ma",
        search_url=lambda q, page: (
            "https://www.avito.ma/fr/maroc/voitures-%C3%A0_vendre"
            f"?o={page}&q={quote_plus(q)}"
        ),
        result_selectors=("article", "[data-testid*='ad']", ".sc-list", ".listing"),
        title_selectors=("h1", "h2", "h3", "[class*='title']", "[class*='Title']"),
        price_selectors=("[class*='price']", "[class*='Price']", "[class*='prix']"),
        location_selectors=("[class*='location']", "[class*='city']", "[class*='region']"),
        time_selectors=("time", "[class*='date']", "[class*='time']"),
    ),
    SourceSpec(
        country="Morocco",
        source="Moteur.ma",
        base_url="https://www.moteur.ma",
        search_url=lambda q, page: (
            "https://www.moteur.ma/fr/voiture/achat-voiture-occasion/"
            f"?page={page}&q={quote_plus(q)}"
        ),
        result_selectors=("article", ".listing", ".card", "[class*='annonce']"),
        title_selectors=("h1", "h2", "h3", "[class*='title']", "[class*='Title']"),
        price_selectors=("[class*='price']", "[class*='Price']", "[class*='prix']"),
        location_selectors=("[class*='location']", "[class*='city']", "[class*='ville']"),
        time_selectors=("time", "[class*='date']", "[class*='time']"),
    ),
]

DISCUSSION_SOURCES = [
    DiscussionSourceSpec(
        country="Algeria",
        source="Reddit r/algeria",
        source_type="reddit_search",
        base_url="https://www.reddit.com",
        search_url=lambda q, page: (
            "https://www.reddit.com/r/algeria/search.json"
            f"?q={quote_plus(q)}&restrict_sr=1&sort=new&t=month&limit=25"
        ),
    ),
    DiscussionSourceSpec(
        country="Morocco",
        source="Reddit r/Morocco",
        source_type="reddit_search",
        base_url="https://www.reddit.com",
        search_url=lambda q, page: (
            "https://www.reddit.com/r/Morocco/search.json"
            f"?q={quote_plus(q)}&restrict_sr=1&sort=new&t=month&limit=25"
        ),
    ),
    DiscussionSourceSpec(
        country="Libya",
        source="Reddit r/Libya",
        source_type="reddit_search",
        base_url="https://www.reddit.com",
        search_url=lambda q, page: (
            "https://www.reddit.com/r/Libya/search.json"
            f"?q={quote_plus(q)}&restrict_sr=1&sort=new&t=month&limit=25"
        ),
    ),
]
