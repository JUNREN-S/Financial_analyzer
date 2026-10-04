# Financial Analyzer

**Enterprise comprehensive evaluation & risk assessment for Chinese A-share companies, built on Entropy Weight Method + TOPSIS.**

An OpenClaw skill. Chinese-language docs live in [SKILL.md](SKILL.md); this README is the English quick-start.

## Features

| Capability | Description |
|---|---|
| Data ingestion | Online fetch via [AkShare](https://akshare.akfamily.xyz/) or local Excel import |
| Objective weighting | Entropy Weight Method (no subjective weights) |
| Comprehensive scoring | TOPSIS ranking against the ideal solution |
| Risk assessment | Five-dimension risk identification |
| Case screening | "New quality productive forces" (新质生产力) theme fit evaluation |
| Company profiling | 9-type attribute classification from core indicators |
| Peer recommendation | Similar-company suggestions for unsuitable targets |
| Regression prep | RD-intensity vs growth regression data export |
| Visualization | Radar charts, heatmaps, ranking charts, risk matrix |

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.10+. Dependencies: pandas, numpy, akshare, matplotlib, seaborn, requests, lxml.

## Usage

```bash
cd scripts

# 1. Online A-share data
python main.py --demo                    # demo (5 companies)
python main.py                           # full pool (37 companies)
python main.py -c 600519 000858 000333   # custom tickers

# 2. Local Excel (intelligent repair: extracts company names and
#    fetches complete data online when the file is incomplete)
python main.py --excel /path/to/data.xlsx --sheet Sheet1

# 3. Natural-language query (Chinese)
python main.py --query "分析一下茅台、五粮液和美的集团"

# 4. Pre-screening (new quality productive forces theme)
python main.py --screening data/companies.csv --target "智算云科"

# 5. Case screening + similar-company recommendation
python finance_case_tool.py --data data/companies.csv --company "智算云科"
```

## Output

Each run writes to `result/test_<n>/` (gitignored):

- `ranking.csv`, `dimension_scores.csv`, `indicator_weights.csv`, `risk_assessment.csv`, `raw_data.csv`
- Charts: radar, heatmap, risk matrix, dimension comparison, ranking, weight distribution
- `analysis_report.txt`

## Project structure

```
config/indicators.py      # indicator system configuration
scripts/
  main.py                 # entry point
  data_fetcher.py         # AkShare online data
  excel_loader.py         # Excel import
  intelligent_repair.py   # extract company names -> fetch complete data online
  nlp_input.py            # natural-language company parsing
  case_selector.py        # theme screening
  finance_case_tool.py    # case evaluation + peer recommendation
  company_attribute_profiler.py
  calculator.py           # entropy weight + TOPSIS engine
  risk_assessor.py        # five-dimension risk assessment
  visualizer.py           # charts
  test_api.py
```

Full documentation (Chinese): [SKILL.md](SKILL.md)
