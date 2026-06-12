# Data Warehouse & Analytics Dashboard

> End-to-end data engineering project — ETL pipeline → Star schema warehouse → Interactive analytics dashboard.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-green) ![Plotly](https://img.shields.io/badge/Plotly-5.x-orange) ![Tests](https://img.shields.io/badge/Tests-85%20passing-brightgreen)

---

## Live Dashboard

8 sections · 18 interactive Plotly charts · Real-time data from SQLite warehouse

| Section | Charts |
|---|---|
| Overview | KPI cards, revenue trend, category donut, region bar, LTV donut |
| Revenue Trends | Monthly revenue+profit+orders, year-over-year grouped bar |
| Region & Segment | Region bar, segment donut, region detail comparison |
| Sales Channels | Channel bar, channel pie, channel detail with margin |
| Top Products | Revenue vs profit bar, revenue vs margin scatter |
| Categories | Category donut, margin bar, cost vs profit stacked bar |
| Customer LTV | Tier donut, revenue concentration, top 10 customers |
| Cohort Analysis | Monthly cohort revenue heatmap |
| Campaigns & ROI | Budget vs revenue scatter, ROI by type, all campaigns bar |

---

## Architecture

```
Raw Sources (CSV/JSON)
       │
  ┌────▼────┐    ┌──────────┐    ┌────────────┐
  │ Extract │───▶│Transform │───▶│   Load     │
  └─────────┘    └──────────┘    └─────┬──────┘
                                       │ Staging DB
                               ┌───────▼────────┐
                               │  Star Schema   │
                               │  fact_sales    │
                               │  dim_customer  │
                               │  dim_product   │
                               │  dim_date      │
                               │  dim_campaign  │
                               └───────┬────────┘
                                       │ 10 KPI Views
                               ┌───────▼────────┐
                               │ Flask + Plotly │
                               │   Dashboard    │
                               └────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data Processing | Pandas, NumPy |
| Database | SQLite / PostgreSQL |
| ORM | SQLAlchemy |
| Web Framework | Flask 3.x |
| Charts | Plotly.js |
| Testing | pytest (85 tests) |
| Logging | loguru |

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/data-warehouse-analytics
cd data-warehouse-analytics

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

# Run full pipeline (generate data → ETL → warehouse → analytics)
python run_pipeline.py

# Run all 85 tests
python -m pytest tests/ -v

# Launch dashboard
python dashboard/app.py
# Open: http://127.0.0.1:5000
```

## Data Model

| Table | Rows | Description |
|---|---|---|
| `fact_sales` | 10,528 | One row per order line item (grain) |
| `dim_date` | 1,096 | Every calendar day 2022–2024 |
| `dim_customer` | 500 | Customer demographics & segments |
| `dim_product` | 50 | Product catalog with pricing |
| `dim_campaign` | 20 | Marketing campaigns |

## Key Metrics (Sample Data)

- **Total Revenue:** ₹41.38 Crore across 3 years
- **Total Profit:** ₹18.00 Crore at 41% avg margin
- **Orders:** 3,024 completed orders
- **Top Category:** Electronics (54.7% of revenue)
- **Top Region:** North India (₹10.78 Cr)

## Project Structure

```
data-warehouse-analytics/
├── data/raw/              ← Source CSV + JSON files
├── etl/
│   ├── generate_data.py   ← Synthetic data generator
│   ├── extract.py         ← Read & validate raw files
│   ├── transform.py       ← Clean, enrich, validate
│   └── load.py            ← Load to staging DB
├── warehouse/
│   ├── schema.sql         ← Star schema DDL
│   └── build_warehouse.py ← Builds fact + dim tables
├── analytics/
│   ├── kpi_queries.sql    ← 10 KPI SQL views
│   └── run_analytics.py   ← Runs & exports KPIs
├── dashboard/
│   ├── app.py             ← Flask application (11 API routes)
│   ├── templates/         ← HTML dashboard
│   └── static/            ← CSS + Plotly JS
├── tests/                 ← 85 tests (ETL + Warehouse + Dashboard)
├── run_pipeline.py        ← Master pipeline runner
└── requirements.txt
```

---


