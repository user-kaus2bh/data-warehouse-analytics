# Data Warehouse & Analytics Dashboard

> End-to-end data pipeline — from raw CSV/JSON sources to an interactive analytics dashboard.
> Built in Python with ETL pipelines, a star-schema warehouse, and a Flask/Plotly dashboard.

---

## Architecture

```
Raw Sources (CSV/JSON)
       │
       ▼
  ┌─────────┐    ┌───────────┐    ┌──────────────┐
  │ Extract │ ─► │ Transform │ ─► │    Load      │
  │ (read)  │    │ (clean)   │    │ (SQLite DB)  │
  └─────────┘    └───────────┘    └──────────────┘
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  Star Schema      │
                               │  fact_sales       │
                               │  dim_customer     │
                               │  dim_product      │
                               │  dim_date         │
                               └──────────────────┘
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  Analytics Views  │
                               │  KPI Queries      │
                               └──────────────────┘
                                         │
                                         ▼
                               ┌──────────────────┐
                               │  Dashboard (Flask)│
                               │  Sales · Marketing│
                               └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data Processing | Pandas, NumPy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM / DB Layer | SQLAlchemy |
| Dashboard | Flask + Plotly |
| Testing | pytest |
| Logging | loguru |
| Fake Data | Faker |

## Project Structure

```
data-warehouse-analytics/
├── data/
│   ├── raw/               ← source CSVs & JSON (generated)
│   └── processed/         ← cleaned CSVs (ETL output)
├── etl/
│   ├── config.py          ← settings loader (.env)
│   ├── logger.py          ← structured logging
│   ├── generate_data.py   ← synthetic data generator
│   ├── extract.py         ← read & validate raw files
│   ├── transform.py       ← clean, enrich, validate
│   └── load.py            ← load into staging DB
├── warehouse/
│   ├── schema.sql         ← star schema DDL
│   └── models/            ← fact & dimension SQL models
├── analytics/
│   └── kpi_queries.sql    ← business KPI queries
├── dashboard/
│   ├── app.py             ← Flask application
│   ├── templates/         ← HTML templates
│   └── static/            ← CSS, JS, chart assets
├── tests/
│   └── test_etl.py        ← 19 unit + integration tests
├── run_pipeline.py        ← main pipeline runner
├── requirements.txt
├── .env.example
└── .gitignore
```

## Quick Start

```bash
# 1. Clone & install
git clone https://github.com/yourusername/data-warehouse-analytics
cd data-warehouse-analytics
pip install -r requirements.txt

# 2. Configure
cp .env.example .env

# 3. Run the full pipeline (generate data → ETL → load to DB)
python run_pipeline.py

# 4. Run tests
python -m pytest tests/ -v

# 5. Launch dashboard (Day 3)
python dashboard/app.py
```

## Day-by-Day Progress

### ✅ Day 1 — ETL Pipeline & Staging Layer
- [x] Synthetic data generator (500 customers, 50 products, 5000 orders, 20 campaigns)
- [x] Extract: reads CSV + JSON with schema validation
- [x] Transform: null handling, type coercion, deduplication, derived columns
- [x] Load: staging tables in SQLite with referential integrity checks
- [x] Data quality report (null %, duplicate counts, row counts)
- [x] 19 unit + integration tests — all passing

### 🔄 Day 2 — Data Warehouse & Star Schema
- [ ] Star schema DDL (fact_sales, dim_customer, dim_product, dim_date, dim_campaign)
- [ ] SQL transformation models
- [ ] Analytics views (monthly revenue, customer LTV, campaign ROI)
- [ ] KPI query library

### 📊 Day 3 — Dashboard & GitHub Polish
- [ ] Flask API + Plotly charts
- [ ] Sales & marketing insights dashboard
- [ ] Architecture diagram
- [ ] Final README + screenshots

---

## Data Model (Staging)

| Table | Rows | Description |
|---|---|---|
| `stg_customers` | 500 | Customer demographics & segments |
| `stg_products` | 50 | Product catalog with pricing |
| `stg_orders` | 5,000 | Sales orders 2022–2024 |
| `stg_order_items` | ~10,500 | Line items per order |
| `stg_campaigns` | 20 | Marketing campaigns with spend & ROI |

---

*Built as a portfolio project demonstrating end-to-end data engineering.*
