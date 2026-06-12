"""
dashboard/app.py
────────────────
Flask web application for the Data Warehouse Analytics Dashboard.

Routes:
    GET /                    → Main dashboard HTML page
    GET /api/kpis            → Top-line KPI summary cards
    GET /api/revenue/monthly → Monthly revenue trend (line chart)
    GET /api/revenue/yoy     → Year-over-year comparison (grouped bar)
    GET /api/revenue/region  → Revenue by region (horizontal bar)
    GET /api/revenue/segment → Revenue by customer segment (donut)
    GET /api/revenue/channel → Sales channel performance (bar)
    GET /api/products/top    → Top 10 products by revenue (bar)
    GET /api/products/category → Category breakdown (treemap data)
    GET /api/campaigns/roi   → Campaign ROI scatter data
    GET /api/customers/ltv   → Customer LTV tier distribution (donut)
    GET /api/customers/cohort→ Cohort revenue heatmap data

Run:
    python dashboard/app.py
    Then open: http://127.0.0.1:5000
"""

import sys
import json
from pathlib import Path
from flask import Flask, jsonify, render_template, abort
from sqlalchemy import create_engine, text
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))
from config import DB_URL
from logger import get_logger

log = get_logger("dashboard")

app = Flask(__name__, template_folder="templates", static_folder="static")
engine = create_engine(DB_URL, echo=False)


# ─── Helper ───────────────────────────────────────────────────────────────────

def query(sql: str, params: dict = None) -> list[dict]:
    """Execute SQL and return list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]


def safe_float(val, decimals=2):
    if val is None:
        return 0.0
    return round(float(val), decimals)


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── API: KPI Summary Cards ───────────────────────────────────────────────────

@app.route("/api/kpis")
def api_kpis():
    rows = query("""
        SELECT
            COUNT(DISTINCT order_id)               AS total_orders,
            COUNT(DISTINCT customer_key)           AS unique_customers,
            ROUND(SUM(line_revenue), 0)            AS total_revenue,
            ROUND(SUM(line_profit), 0)             AS total_profit,
            ROUND(AVG(line_margin_pct), 1)         AS avg_margin,
            ROUND(SUM(line_revenue) /
                  NULLIF(COUNT(DISTINCT order_id),0), 0) AS avg_order_value,
            SUM(quantity)                          AS total_units
        FROM fact_sales WHERE is_revenue = 1
    """)
    r = rows[0]

    # Growth: compare 2024 vs 2023
    growth = query("""
        SELECT year, ROUND(SUM(total_revenue),0) AS rev
        FROM vw_monthly_revenue GROUP BY year ORDER BY year
    """)
    yoy_growth = 0
    if len(growth) >= 2:
        prev = growth[-2]["rev"] or 1
        curr = growth[-1]["rev"] or 0
        yoy_growth = round((curr - prev) / prev * 100, 1)

    return jsonify({
        "total_revenue":    safe_float(r["total_revenue"], 0),
        "total_profit":     safe_float(r["total_profit"], 0),
        "total_orders":     int(r["total_orders"] or 0),
        "unique_customers": int(r["unique_customers"] or 0),
        "avg_margin":       safe_float(r["avg_margin"], 1),
        "avg_order_value":  safe_float(r["avg_order_value"], 0),
        "total_units":      int(r["total_units"] or 0),
        "yoy_growth":       yoy_growth,
    })


# ─── API: Monthly Revenue Trend ───────────────────────────────────────────────

@app.route("/api/revenue/monthly")
def api_monthly():
    rows = query("""
        SELECT year_month, year, month_name, month,
               ROUND(total_revenue,0)  AS revenue,
               ROUND(total_profit,0)   AS profit,
               total_orders,
               ROUND(avg_margin_pct,1) AS margin,
               unique_customers,
               ROUND(avg_order_value,0) AS aov
        FROM vw_monthly_revenue ORDER BY year, month
    """)
    return jsonify(rows)


# ─── API: Year-over-Year Comparison ──────────────────────────────────────────

@app.route("/api/revenue/yoy")
def api_yoy():
    rows = query("""
        SELECT month, month_name,
               ROUND(revenue_2022,0) AS revenue_2022,
               ROUND(revenue_2023,0) AS revenue_2023,
               ROUND(revenue_2024,0) AS revenue_2024,
               growth_22_23_pct, growth_23_24_pct
        FROM vw_yoy_comparison ORDER BY month
    """)
    return jsonify(rows)


# ─── API: Revenue by Region ───────────────────────────────────────────────────

@app.route("/api/revenue/region")
def api_region():
    rows = query("""
        SELECT region,
               ROUND(SUM(total_revenue),0)  AS revenue,
               ROUND(SUM(total_profit),0)   AS profit,
               SUM(total_orders)            AS orders,
               SUM(unique_customers)        AS customers,
               ROUND(AVG(avg_margin_pct),1) AS avg_margin
        FROM vw_revenue_by_region
        GROUP BY region ORDER BY revenue DESC
    """)
    return jsonify(rows)


# ─── API: Revenue by Segment ──────────────────────────────────────────────────

@app.route("/api/revenue/segment")
def api_segment():
    rows = query("""
        SELECT segment,
               ROUND(SUM(total_revenue),0)  AS revenue,
               ROUND(SUM(total_profit),0)   AS profit,
               SUM(total_orders)            AS orders,
               ROUND(AVG(avg_margin_pct),1) AS avg_margin
        FROM vw_revenue_by_segment
        GROUP BY segment ORDER BY revenue DESC
    """)
    return jsonify(rows)


# ─── API: Sales Channel ───────────────────────────────────────────────────────

@app.route("/api/revenue/channel")
def api_channel():
    rows = query("""
        SELECT channel,
               ROUND(SUM(total_revenue),0)  AS revenue,
               ROUND(SUM(total_profit),0)   AS profit,
               SUM(total_orders)            AS orders,
               ROUND(AVG(avg_margin_pct),1) AS avg_margin,
               ROUND(AVG(avg_order_value),0) AS avg_order_value
        FROM vw_channel_performance
        GROUP BY channel ORDER BY revenue DESC
    """)
    return jsonify(rows)


# ─── API: Top Products ────────────────────────────────────────────────────────

@app.route("/api/products/top")
def api_top_products():
    rows = query("""
        SELECT product_name, category, price_band,
               ROUND(total_revenue,0)   AS revenue,
               ROUND(total_profit,0)    AS profit,
               avg_margin_pct           AS margin,
               total_units_sold         AS units,
               times_ordered, unique_buyers
        FROM vw_top_products LIMIT 15
    """)
    return jsonify(rows)


# ─── API: Category Performance ────────────────────────────────────────────────

@app.route("/api/products/category")
def api_category():
    rows = query("""
        SELECT category,
               ROUND(SUM(total_revenue),0)   AS revenue,
               ROUND(SUM(total_profit),0)    AS profit,
               ROUND(SUM(total_cost),0)      AS cost,
               ROUND(AVG(avg_margin_pct),1)  AS avg_margin,
               SUM(total_units_sold)         AS units,
               SUM(total_orders)             AS orders
        FROM vw_category_performance
        GROUP BY category ORDER BY revenue DESC
    """)
    return jsonify(rows)


# ─── API: Campaign ROI ────────────────────────────────────────────────────────

@app.route("/api/campaigns/roi")
def api_campaigns():
    rows = query("""
        SELECT campaign_name, campaign_type, goal,
               ROUND(campaign_budget,0)        AS budget,
               ROUND(attributed_revenue,0)     AS revenue,
               ROUND(attributed_profit,0)      AS profit,
               roi_pct,
               attributed_orders               AS orders,
               attributed_customers            AS customers
        FROM vw_campaign_roi
        ORDER BY attributed_revenue DESC
    """)
    return jsonify(rows)


# ─── API: Customer LTV Tiers ──────────────────────────────────────────────────

@app.route("/api/customers/ltv")
def api_ltv():
    tiers = query("""
        SELECT ltv_tier,
               COUNT(*)                   AS customers,
               ROUND(SUM(total_revenue),0) AS revenue,
               ROUND(AVG(total_orders),1)  AS avg_orders,
               ROUND(AVG(avg_order_value),0) AS avg_order_value
        FROM vw_customer_ltv
        GROUP BY ltv_tier
        ORDER BY revenue DESC
    """)
    top10 = query("""
        SELECT name, segment, region, ltv_tier,
               total_orders,
               ROUND(total_revenue,0) AS revenue,
               ROUND(avg_order_value,0) AS avg_order_value
        FROM vw_customer_ltv
        ORDER BY total_revenue DESC LIMIT 10
    """)
    return jsonify({"tiers": tiers, "top10": top10})


# ─── API: Cohort Heatmap ──────────────────────────────────────────────────────

@app.route("/api/customers/cohort")
def api_cohort():
    rows = query("""
        SELECT cohort_month, activity_month,
               active_customers,
               ROUND(cohort_revenue,0) AS revenue
        FROM vw_cohort_monthly
        ORDER BY cohort_month, activity_month
        LIMIT 300
    """)
    return jsonify(rows)


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting dashboard at http://127.0.0.1:5000")
    app.run(debug=True, port=5000, host="0.0.0.0")
