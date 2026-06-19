# Data Warehouse & Analytics Dashboard

> End-to-end data engineering project — ETL pipeline → Star schema warehouse → Interactive analytics dashboard → Live on Render.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-green) ![Plotly](https://img.shields.io/badge/Plotly-5.x-orange) ![Tests](https://img.shields.io/badge/Tests-85%20passing-brightgreen) ![Render](https://img.shields.io/badge/Hosted-Render-purple)

---

## 🚀 Live Demo

**[View Dashboard →](https://data-warehouse-analytics.onrender.com)**

> Hosted on Render free tier — may take 30–60 seconds to wake up on first visit.

---

## Architecture

```
Raw Sources (CSV/JSON)
       │
  ┌────▼────┐    ┌──────────┐    ┌────────────┐
  │ Extract │───▶│Transform │───▶│   Load     │
  └─────────┘    └──────────┘    └────────────┘
                                       │ Staging DB (SQLite)
                               ┌───────▼────────┐
                               │  Star Schema   │
                               │  fact_sales    │
                               │  dim_customer  │
                               │  dim_product   │
                               │  dim_date      │
                               │  dim_campaign  │
                               └───────┬────────┘
                                       │ 10 KPI SQL Views
                               ┌───────▼────────┐
                               │ Flask REST API │
                               │ 11 Endpoints   │
                               └───────┬────────┘
                                       │
                               ┌───────▼────────┐
                               │ Plotly.js UI  │
                               │ 8 Sections    │
                               │ 18 Charts     │
                               └────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Data Processing | Pandas, NumPy |
| Database | SQLite (warehouse.db committed to repo) |
| ORM | SQLAlchemy |
| Web Framework | Flask 3.x |
| WSGI Server | Gunicorn |
| Charts | Plotly.js |
| Testing | pytest (85 tests) |
| Hosting | Render |

## Quick Start (Local)

```bash
git clone https://github.com/YOUR_USERNAME/data-warehouse-analytics
cd data-warehouse-analytics

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

# Run full pipeline (generate → ETL → warehouse → analytics)
python run_pipeline.py

# Run all 85 tests
python -m pytest tests/ -v

# Launch dashboard
python dashboard/app.py
# Open: http://127.0.0.1:5000
```

## Deploying to Render (Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Deploy**
5. Done — live in ~3 minutes

## Dashboard Sections

| Section | Charts |
|---|---|
| Overview | KPI cards, revenue trend, category donut, region bar, LTV donut |
| Revenue Trends | Monthly revenue+profit+orders, year-over-year comparison |
| Region & Segment | Region bars, customer segment donut, region detail |
| Sales Channels | Channel bar, channel pie, channel metrics comparison |
| Top Products | Revenue vs profit bar, revenue vs margin scatter |
| Categories | Category donut, margin bar, cost vs profit stacked bar |
| Customer LTV | Tier donut, revenue concentration, top 10 customers |
| Cohort Analysis | Monthly cohort revenue heatmap |
| Campaigns & ROI | Budget vs revenue scatter, ROI by type, all campaigns bar |

## Key Metrics (Sample Data — 2022–2024)

| Metric | Value |
|---|---|
| Total Revenue | ₹41.38 Crore |
| Total Profit | ₹18.00 Crore |
| Avg Margin | 41% |
| Completed Orders | 3,024 |
| Unique Customers | 498 |
| Top Category | Electronics (54.7% of revenue) |
| YoY Growth (2023→2024) | +14.3% |

## Project Structure

```
data-warehouse-analytics/
├── data/
│   ├── raw/               ← Source CSV + JSON (gitignored)
│   └── warehouse.db       ← SQLite warehouse (committed — used by Render)
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
│   ├── app.py             ← Flask app (11 API routes)
│   ├── templates/         ← HTML dashboard
│   └── static/            ← CSS + Plotly JS
├── tests/                 ← 85 automated tests
├── Procfile               ← Render/Gunicorn start command
├── render.yaml            ← Render deployment config
├── run_pipeline.py        ← Master pipeline runner
└── requirements.txt
```

---


