# Vehicle Model Frequency Radar MVP

This Python MVP collects and counts how often target vehicle models and related keywords appear on public vehicle listing pages.

It intentionally does **not** create opportunity scores, recommendations, or market judgments. Outputs are limited to counts, frequencies, weekly changes, related keyword counts, price ranges, and source links.

## Markets and Sources

- Algeria: Ouedkniss
- Libya: OpenSooq
- Morocco: Avito
- Morocco: Moteur.ma, when accessible

The scraper uses configurable search URL templates in `vehicle_frequency_radar/config.py`. Public listing sites change markup often, so the first optimization point is usually updating those templates or selectors after checking a live page.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, use `python3` if `python` is not available:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional, only if a site requires JavaScript rendering in a later extension:

```bash
pip install ".[playwright]"
playwright install chromium
```

## Run

Run a small, respectful first pass:

```bash
python -m vehicle_frequency_radar --out output --max-pages 1 --no-fetch-details
```

Try Playwright only when plain HTML returns no parseable listings:

```bash
python -m vehicle_frequency_radar --out output --renderer auto --max-pages 1 --no-fetch-details
```

Run with listing detail pages included:

```bash
python -m vehicle_frequency_radar --out output --max-pages 1
```

Limit to a source or keyword while tuning selectors:

```bash
python -m vehicle_frequency_radar --out output --source Avito --keyword "Dacia Duster" --max-pages 1
```

Append a new run to existing CSVs before deduplication and weekly aggregation:

```bash
python -m vehicle_frequency_radar --out output --append --max-pages 1
```

## Compliance Defaults

- Fetches `robots.txt` before scraping each host.
- Strict mode is enabled by default: if `robots.txt` is unavailable, the host is skipped.
- Explicit `Disallow` rules are respected.
- Per-host request delays default to at least 3 seconds, plus any crawl delay declared in `robots.txt`.
- Login-only pages are not accessed.
- Detail pages can be skipped with `--no-fetch-details` to reduce request volume.
- Playwright is opt-in via `--renderer auto` or `--renderer playwright`.

If you need a discovery run where `robots.txt` is temporarily unreachable, use:

```bash
python -m vehicle_frequency_radar --non-strict-robots --out output --max-pages 1 --no-fetch-details
```

Use that only when you have separately confirmed that public search pages may be fetched.

## Outputs

The run writes six CSV files:

1. `raw_listings.csv`
2. `cleaned_listings.csv`
3. `model_frequency_by_market.csv`
4. `model_frequency_change_weekly.csv`
5. `related_keyword_frequency.csv`
6. `price_range_by_model_market.csv`

Listing fields include:

- `scrape_date`
- `country`
- `source`
- `search_keyword`
- `matched_model`
- `listing_title`
- `title_text_raw`
- `description_text_raw`
- `price`
- `currency`
- `location`
- `posted_time`
- `listing_url`
- `related_keywords`

`cleaned_listings.csv` also includes normalized title/location fields, numeric price, and the composite dedupe key.

## Deduplication

The pipeline deduplicates by:

- `listing_url`
- `title_normalized + price_numeric + location_normalized`

This catches duplicates caused by searching multiple aliases, for example `MG5` and `MG 5`.

## How To Optimize This MVP

- Tune one source at a time with `--source` and `--keyword`.
- Start with `--no-fetch-details`; enable detail pages only when title-only related keyword counts are insufficient.
- Update source selectors in `config.py` after inspecting live HTML.
- Keep `max-pages` low until parsing quality is verified.
- Use `--append` weekly so `model_frequency_change_weekly.csv` can compare against prior weeks.
- Add a project-specific contact in `USER_AGENT` before running at scale.
- Use `--renderer auto` only for sources where public pages render no listings through plain `requests`.

## Tests

```bash
pip install ".[dev]"
pytest
```
