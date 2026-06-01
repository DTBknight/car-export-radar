# Vehicle Model Discussion Heat Radar

这个项目现在定位为“车型讨论热度雷达”，目标是观察目标车型在公开讨论、经销、采购、进口、贸易语境中的出现频率。

它不做机会评分，不做商业建议，只展示公开提及次数、经销/采购信号词、来源覆盖和证据链接。

## 看网页

GitHub Pages 地址：

https://dtbknight.github.io/car-export-radar/

页面自动读取 `data/latest.json`，不需要手动上传 CSV。

## 默认抓取什么

默认模式是讨论热度：

```bash
python -m vehicle_frequency_radar --mode mentions --out output --max-pages 1
```

当前先从无需登录的公开 Reddit 搜索开始：

- Algeria: `Reddit r/algeria`
- Morocco: `Reddit r/Morocco`
- Libya: `Reddit r/Libya`

## 增加数据源

复制示例来源文件：

```bash
mkdir -p config
cp config/discussion_sources.example.csv config/discussion_sources.csv
```

把要启用的行改成 `enabled=true`。`url_template` 支持：

- `{query}`：车型关键词
- `{page}`：页码
- `{api_key}`：从环境变量读取的 API key

公开经销商/贸易商网站用 `source_type=public_html`。YouTube 建议走官方 API：

```bash
export YOUTUBE_API_KEY="你的 key"
python -m vehicle_frequency_radar --mode mentions --out output --discussion-source-file config/discussion_sources.csv
```

不要抓登录墙、私密群组，或绕过反爬限制。

## 车源页作为辅助

车源页仍保留为辅助供给参考，需要单独运行：

```bash
python -m vehicle_frequency_radar --mode supply --out output_supply --max-pages 1 --no-fetch-details
```

## 输出文件

讨论热度模式生成：

- `raw_mentions.csv`：原始公开提及记录
- `cleaned_mentions.csv`：清洗去重后的公开提及
- `model_heat_by_market.csv`：车型在各市场的公开提及次数
- `discussion_heat_change_weekly.csv`：周度讨论变化
- `trader_signal_frequency.csv`：经销、采购、进口语境信号词频次
- `source_coverage.csv`：来源覆盖情况
- `evidence_samples.csv`：抽样证据链接

网页使用 `data/latest.json`，这个文件由 CSV 汇总生成：

```bash
python -m vehicle_frequency_radar.site --input output --out data/latest.json
```

## 每天自动更新

GitHub Actions 里的 `Daily vehicle discussion radar scrape` 会每天运行，也可以手动点 `Run workflow`。

流程是：

1. 抓取公开讨论提及
2. 生成 CSV
3. 生成 `data/latest.json`
4. 提交到仓库
5. GitHub Pages 自动重新部署网页

## 怎么判断数据是否属实

看证据链，不看页面数字本身：

- `discussion_url` 是原文证据链接
- `mention_title` / `mention_text_raw` 是抓取到的标题和文本
- `matched_model` 是命中的车型
- `trader_signal_keywords` 是命中的经销、采购、进口信号词
- `scrape_date` 和 `published_time` 用来判断时间

抽样打开 `discussion_url` 对照原文，是验证数据的主要方法。

## 后续扩展方向

优先增加这些来源：

- 公开经销商页面
- 公开进口/贸易商页面
- YouTube 官方 API 的标题、描述、发布时间和互动数据
- Facebook/Instagram/TikTok 只通过官方 API、合规数据服务，或无需登录的公开页面种子采集

不要抓登录墙、私密群组或绕过反爬限制。

## 本地测试

```bash
pip install -r requirements.txt
pytest
```
