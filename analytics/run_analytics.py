"""
analytics/run_analytics.py
──────────────────────────
Creates all 10 KPI views and prints summary reports to the console.
Also exports each view as a CSV to data/processed/analytics/.

Run:
    python analytics/run_analytics.py
"""

import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))
from config import DB_URL, DB_PATH
from logger import get_logger

log = get_logger("analytics")

ANALYTICS_DIR = Path(__file__).parent.parent / "data" / "processed" / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)


def get_engine():
    return create_engine(DB_URL, echo=False)


def create_views(engine):
    sql_path = Path(__file__).parent / "kpi_queries.sql"
    sql = sql_path.read_text(encoding="utf-8")
    statements = [
        s.strip() for s in sql.split(";")
        if s.strip() and not s.strip().startswith("--")
    ]
    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                if "already exists" not in str(e):
                    raise
        conn.commit()
    log.info("All 10 KPI views created ✓")


def run_kpi_reports(engine):
    log.info("─── KPI REPORTS ─────────────────────────────────────────")

    # ── 1. Top-line summary ────────────────────────────────────────────────────
    summary = pd.read_sql("""
        SELECT
            COUNT(DISTINCT order_id)     AS total_orders,
            COUNT(DISTINCT customer_key) AS unique_customers,
            SUM(line_revenue)            AS total_revenue,
            SUM(line_profit)             AS total_profit,
            ROUND(AVG(line_margin_pct),1) AS avg_margin_pct,
            ROUND(SUM(line_revenue)/COUNT(DISTINCT order_id),2) AS avg_order_value
        FROM fact_sales WHERE is_revenue = 1
    """, engine)
    s = summary.iloc[0]
    log.info("TOP-LINE METRICS")
    log.info(f"  Total Orders     : {int(s['total_orders']):,}")
    log.info(f"  Unique Customers : {int(s['unique_customers']):,}")
    log.info(f"  Total Revenue    : ₹{s['total_revenue']:,.0f}")
    log.info(f"  Total Profit     : ₹{s['total_profit']:,.0f}")
    log.info(f"  Avg Margin       : {s['avg_margin_pct']}%")
    log.info(f"  Avg Order Value  : ₹{s['avg_order_value']:,.0f}")

    # ── 2. Revenue by year ─────────────────────────────────────────────────────
    yoy = pd.read_sql("""
        SELECT year, ROUND(SUM(total_revenue),0) as revenue,
               SUM(total_orders) as orders
        FROM vw_monthly_revenue GROUP BY year ORDER BY year
    """, engine)
    log.info("\nREVENUE BY YEAR")
    for _, row in yoy.iterrows():
        log.info(f"  {int(row['year'])}  ₹{row['revenue']:>15,.0f}   {int(row['orders']):,} orders")

    # ── 3. Revenue by region ───────────────────────────────────────────────────
    region = pd.read_sql("""
        SELECT region, ROUND(SUM(total_revenue),0) AS revenue,
               SUM(total_orders) AS orders
        FROM vw_revenue_by_region GROUP BY region ORDER BY revenue DESC
    """, engine)
    log.info("\nREVENUE BY REGION")
    for _, row in region.iterrows():
        log.info(f"  {row['region']:10s}  ₹{row['revenue']:>15,.0f}   {int(row['orders']):,} orders")

    # ── 4. Revenue by segment ──────────────────────────────────────────────────
    seg = pd.read_sql("""
        SELECT segment, ROUND(SUM(total_revenue),0) AS revenue,
               SUM(total_orders) AS orders
        FROM vw_revenue_by_segment GROUP BY segment ORDER BY revenue DESC
    """, engine)
    log.info("\nREVENUE BY CUSTOMER SEGMENT")
    for _, row in seg.iterrows():
        log.info(f"  {row['segment']:12s}  ₹{row['revenue']:>15,.0f}   {int(row['orders']):,} orders")

    # ── 5. Top 5 products ──────────────────────────────────────────────────────
    top5 = pd.read_sql("""
        SELECT product_name, category, total_revenue, avg_margin_pct, total_units_sold
        FROM vw_top_products LIMIT 5
    """, engine)
    log.info("\nTOP 5 PRODUCTS BY REVENUE")
    for _, row in top5.iterrows():
        log.info(f"  {row['product_name']:25s}  ₹{row['total_revenue']:>12,.0f}  margin={row['avg_margin_pct']}%")

    # ── 6. Category summary ────────────────────────────────────────────────────
    cat = pd.read_sql("""
        SELECT category, ROUND(SUM(total_revenue),0) AS revenue,
               ROUND(AVG(avg_margin_pct),1) AS avg_margin
        FROM vw_category_performance GROUP BY category ORDER BY revenue DESC
    """, engine)
    log.info("\nREVENUE BY CATEGORY")
    for _, row in cat.iterrows():
        log.info(f"  {row['category']:15s}  ₹{row['revenue']:>15,.0f}   margin={row['avg_margin']}%")

    # ── 7. Top 5 campaigns ─────────────────────────────────────────────────────
    camp = pd.read_sql("""
        SELECT campaign_name, campaign_type, attributed_revenue, roi_pct
        FROM vw_campaign_roi ORDER BY attributed_revenue DESC LIMIT 5
    """, engine)
    log.info("\nTOP 5 CAMPAIGNS BY ATTRIBUTED REVENUE")
    for _, row in camp.iterrows():
        log.info(f"  {row['campaign_name']:30s}  ₹{row['attributed_revenue']:>12,.0f}   ROI={row['roi_pct']}%")

    # ── 8. LTV tiers ──────────────────────────────────────────────────────────
    ltv = pd.read_sql("""
        SELECT ltv_tier, COUNT(*) AS customers,
               ROUND(SUM(total_revenue),0) AS total_revenue
        FROM vw_customer_ltv
        GROUP BY ltv_tier ORDER BY total_revenue DESC
    """, engine)
    log.info("\nCUSTOMER LTV TIERS")
    for _, row in ltv.iterrows():
        log.info(f"  {row['ltv_tier']:10s}  {int(row['customers']):>4} customers  ₹{row['total_revenue']:>15,.0f}")

    # ── 9. Channel performance ─────────────────────────────────────────────────
    ch = pd.read_sql("""
        SELECT channel, ROUND(SUM(total_revenue),0) AS revenue,
               SUM(total_orders) AS orders
        FROM vw_channel_performance GROUP BY channel ORDER BY revenue DESC
    """, engine)
    log.info("\nREVENUE BY SALES CHANNEL")
    for _, row in ch.iterrows():
        log.info(f"  {row['channel']:15s}  ₹{row['revenue']:>15,.0f}   {int(row['orders']):,} orders")

    log.info("─────────────────────────────────────────────────────────")


def export_views(engine):
    views = [
        "vw_monthly_revenue", "vw_revenue_by_region", "vw_revenue_by_segment",
        "vw_top_products", "vw_category_performance", "vw_campaign_roi",
        "vw_customer_ltv", "vw_cohort_monthly", "vw_channel_performance",
        "vw_yoy_comparison",
    ]
    for view in views:
        df = pd.read_sql(f"SELECT * FROM {view}", engine)
        out = ANALYTICS_DIR / f"{view}.csv"
        df.to_csv(out, index=False)
        log.debug(f"Exported {view} → {out.name}  ({len(df):,} rows)")
    log.info(f"Exported {len(views)} analytics views to data/processed/analytics/")


def main():
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║     ANALYTICS LAYER — DAY 2                             ║")
    log.info("╚══════════════════════════════════════════════════════════╝")
    engine = get_engine()

    log.info("━━━ STEP 1: Create KPI views ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    create_views(engine)

    log.info("━━━ STEP 2: Run KPI reports ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    run_kpi_reports(engine)

    log.info("━━━ STEP 3: Export views to CSV ━━━━━━━━━━━━━━━━━━━━━━━━")
    export_views(engine)

    log.info("Analytics layer complete ✓")


if __name__ == "__main__":
    main()
