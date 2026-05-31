from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Iterable


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def generate_dashboard(input_dir: Path, output_file: Path) -> None:
    model_frequency = read_csv(input_dir / "model_frequency_by_market.csv")
    weekly_change = read_csv(input_dir / "model_frequency_change_weekly.csv")
    related_frequency = read_csv(input_dir / "related_keyword_frequency.csv")
    price_ranges = read_csv(input_dir / "price_range_by_model_market.csv")
    cleaned_listings = read_csv(input_dir / "cleaned_listings.csv")

    payload = {
        "model_frequency": model_frequency,
        "weekly_change": weekly_change,
        "related_frequency": related_frequency,
        "price_ranges": price_ranges,
        "cleaned_listings": cleaned_listings[:300],
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(_render_html(payload), encoding="utf-8")


def _render_html(payload: dict[str, list[dict[str, str]]]) -> str:
    model_frequency = payload["model_frequency"]
    related_frequency = payload["related_frequency"]
    price_ranges = payload["price_ranges"]
    cleaned_listings = payload["cleaned_listings"]
    weekly_change = payload["weekly_change"]

    total_listings = sum(_to_int(row.get("listing_count")) for row in model_frequency)
    unique_models = len({row.get("matched_model", "") for row in model_frequency if row.get("matched_model")})
    markets = len({row.get("country", "") for row in model_frequency if row.get("country")})
    sources = len({row.get("source", "") for row in model_frequency if row.get("source")})

    top_models = sorted(
        model_frequency,
        key=lambda row: _to_int(row.get("listing_count")),
        reverse=True,
    )[:20]
    top_related = sorted(
        related_frequency,
        key=lambda row: _to_int(row.get("listing_count")),
        reverse=True,
    )[:30]

    html_payload = html.escape(json.dumps(payload, ensure_ascii=False))
    return f"""<!doctype html>
  <html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>车辆车型频次雷达</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #18202b;
      --muted: #6b7280;
      --line: #d9dde5;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --warn: #b45309;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    .subtitle {{ margin-top: 8px; color: var(--muted); max-width: 960px; }}
    main {{ padding: 24px 32px 40px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 30px; }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
      gap: 18px;
      align-items: start;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 18px;
    }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    .bar-list {{ display: grid; gap: 10px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(180px, 260px) minmax(120px, 1fr) 54px;
      gap: 10px;
      align-items: center;
      min-height: 30px;
    }}
    .bar-label {{ overflow-wrap: anywhere; font-size: 13px; }}
    .bar-track {{ height: 12px; background: #eef1f5; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; background: var(--accent); }}
    .bar-count {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; background: #fafbfc; }}
    a {{ color: var(--accent-2); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .empty {{
      padding: 20px;
      border: 1px dashed var(--line);
      color: var(--muted);
      border-radius: 8px;
      background: #fbfcfd;
    }}
    .filters {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    select, input {{
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 9px;
      background: #fff;
      color: var(--ink);
    }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .metrics, .grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .bar-count {{ text-align: left; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>车辆车型频次雷达</h1>
    <div class="subtitle">仅统计公开车源页面中的车型与关键词出现次数；不生成机会评分，不输出商业建议。</div>
  </header>
  <main>
    <div class="metrics">
      {_metric("匹配车源数", total_listings)}
      {_metric("匹配车型数", unique_models)}
      {_metric("市场数", markets)}
      {_metric("来源数", sources)}
    </div>
    <div class="grid">
      <div>
        <section>
          <h2>各市场车型频次</h2>
          {_bars(top_models, "matched_model", "listing_count", ["country", "source"])}
        </section>
        <section>
          <h2>各市场车型价格区间</h2>
          {_table(price_ranges, ["country", "source", "matched_model", "currency", "listing_count_with_price", "min_price", "median_price", "max_price"])}
        </section>
        <section>
          <h2>原始车源链接</h2>
          <div class="filters">
            <input id="listingSearch" type="search" placeholder="筛选车源">
            <select id="marketFilter"><option value="">全部市场</option></select>
          </div>
          <div id="listingTable"></div>
        </section>
      </div>
      <div>
        <section>
          <h2>相关关键词频次</h2>
          {_bars(top_related, "related_keyword", "listing_count", ["matched_model", "country"])}
        </section>
        <section>
          <h2>周度变化</h2>
          {_table(weekly_change, ["scrape_week", "country", "source", "matched_model", "listing_count", "previous_week_count", "absolute_change", "pct_change"])}
        </section>
      </div>
    </div>
  </main>
  <script id="payload" type="application/json">{html_payload}</script>
  <script>
    const data = JSON.parse(document.getElementById("payload").textContent);
    const columnLabels = {{
      scrape_week: "抓取周",
      country: "市场",
      source: "来源",
      matched_model: "匹配车型",
      listing_count: "车源数",
      previous_week_count: "上周车源数",
      absolute_change: "变化量",
      pct_change: "变化百分比",
      currency: "币种",
      listing_count_with_price: "有价格车源数",
      min_price: "最低价",
      median_price: "中位价",
      max_price: "最高价",
      listing_title: "标题",
      price: "价格",
      location: "地点",
      listing_url: "原始链接"
    }};
    const listings = data.cleaned_listings || [];
    const marketFilter = document.getElementById("marketFilter");
    const listingSearch = document.getElementById("listingSearch");
    const listingTable = document.getElementById("listingTable");

    [...new Set(listings.map(row => row.country).filter(Boolean))].sort().forEach(country => {{
      const option = document.createElement("option");
      option.value = country;
      option.textContent = country;
      marketFilter.appendChild(option);
    }});

    function escapeHtml(value) {{
      return String(value || "").replace(/[&<>"']/g, char => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }}[char]));
    }}

    function renderListings() {{
      const term = listingSearch.value.toLowerCase();
      const country = marketFilter.value;
      const rows = listings.filter(row => {{
        const haystack = [row.country, row.source, row.matched_model, row.listing_title, row.location].join(" ").toLowerCase();
        return (!country || row.country === country) && (!term || haystack.includes(term));
      }}).slice(0, 100);

      if (!rows.length) {{
        listingTable.innerHTML = '<div class="empty">暂无车源数据。请先运行采集，或上传生成的 CSV。</div>';
        return;
      }}
      listingTable.innerHTML = `
        <table>
          <thead><tr><th>市场</th><th>来源</th><th>匹配车型</th><th>标题</th><th>价格</th><th>地点</th><th>原始链接</th></tr></thead>
          <tbody>${{rows.map(row => `
            <tr>
              <td>${{escapeHtml(row.country)}}</td>
              <td>${{escapeHtml(row.source)}}</td>
              <td>${{escapeHtml(row.matched_model)}}</td>
              <td>${{escapeHtml(row.listing_title)}}</td>
              <td>${{escapeHtml(row.price)}}</td>
              <td>${{escapeHtml(row.location)}}</td>
              <td>${{row.listing_url ? `<a href="${{escapeHtml(row.listing_url)}}" target="_blank" rel="noreferrer">查看</a>` : ""}}</td>
            </tr>`).join("")}}</tbody>
        </table>`;
    }}
    marketFilter.addEventListener("change", renderListings);
    listingSearch.addEventListener("input", renderListings);
    renderListings();
  </script>
</body>
</html>
"""


def _metric(label: str, value: int) -> str:
    return f'<div class="metric"><span>{html.escape(label)}</span><strong>{value}</strong></div>'


def _bars(rows: list[dict[str, str]], label_key: str, value_key: str, context_keys: list[str]) -> str:
    if not rows:
        return '<div class="empty">暂无数据。请先运行采集，或上传生成的 CSV。</div>'
    max_value = max(_to_int(row.get(value_key)) for row in rows) or 1
    parts = ['<div class="bar-list">']
    for row in rows:
        value = _to_int(row.get(value_key))
        width = max(2, round((value / max_value) * 100))
        context = " / ".join(row.get(key, "") for key in context_keys if row.get(key))
        label = row.get(label_key, "")
        parts.append(
            '<div class="bar-row">'
            f'<div class="bar-label"><strong>{html.escape(label)}</strong><br><span>{html.escape(context)}</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>'
            f'<div class="bar-count">{value}</div>'
            "</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def _table(rows: Iterable[dict[str, str]], columns: list[str]) -> str:
    rows = list(rows)
    if not rows:
        return '<div class="empty">暂无数据。</div>'
    header = "".join(f"<th>{html.escape(_column_label(column))}</th>" for column in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns)
        + "</tr>"
        for row in rows[:80]
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _to_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def _column_label(column: str) -> str:
    labels = {
        "scrape_week": "抓取周",
        "country": "市场",
        "source": "来源",
        "matched_model": "匹配车型",
        "listing_count": "车源数",
        "previous_week_count": "上周车源数",
        "absolute_change": "变化量",
        "pct_change": "变化百分比",
        "currency": "币种",
        "listing_count_with_price": "有价格车源数",
        "min_price": "最低价",
        "median_price": "中位价",
        "max_price": "最高价",
        "listing_title": "标题",
        "price": "价格",
        "location": "地点",
        "listing_url": "原始链接",
    }
    return labels.get(column, column)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static HTML dashboard from radar CSV outputs.")
    parser.add_argument("--input", default="output", help="Directory containing generated CSV outputs.")
    parser.add_argument("--out", default="output/dashboard.html", help="HTML file to write.")
    args = parser.parse_args()

    generate_dashboard(Path(args.input), Path(args.out))
    print(f"Wrote dashboard to {args.out}")


if __name__ == "__main__":
    main()
