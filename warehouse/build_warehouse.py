"""
warehouse/build_warehouse.py
────────────────────────────
Reads the 5 staging tables produced by Day 1's ETL pipeline and
populates the star-schema warehouse tables:

    dim_date        → every calendar day 2022-01-01 → 2024-12-31
    dim_customer    → one row per customer
    dim_product     → one row per product
    dim_campaign    → one row per marketing campaign
    fact_sales      → one row per order line item (grain)

Run:
    python warehouse/build_warehouse.py
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))
from config  import DB_URL, DB_PATH
from logger  import get_logger

log = get_logger("warehouse")


# ─── Engine ───────────────────────────────────────────────────────────────────

def get_engine():
    return create_engine(DB_URL, echo=False)


# ─── Schema setup ─────────────────────────────────────────────────────────────

def create_schema(engine):
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--") and "CREATE INDEX" not in s.upper()]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()
    log.info("Schema created (all dim + fact tables)")


# ─── dim_date ─────────────────────────────────────────────────────────────────

def build_dim_date(engine):
    log.info("Building dim_date …")
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="D")

    def fiscal_year(dt):
        return dt.year if dt.month >= 4 else dt.year - 1

    def fiscal_quarter(dt):
        m = dt.month
        if m in (4, 5, 6):   return 1
        if m in (7, 8, 9):   return 2
        if m in (10, 11, 12): return 3
        return 4

    rows = []
    for d in dates:
        rows.append({
            "date_key":        int(d.strftime("%Y%m%d")),
            "full_date":       d.strftime("%Y-%m-%d"),
            "year":            d.year,
            "quarter":         d.quarter,
            "month":           d.month,
            "month_name":      d.strftime("%B"),
            "week":            int(d.isocalendar()[1]),
            "day_of_month":    d.day,
            "day_of_week":     d.isoweekday(),   # 1=Mon … 7=Sun
            "day_name":        d.strftime("%A"),
            "is_weekend":      int(d.isoweekday() >= 6),
            "is_month_start":  int(d.is_month_start),
            "is_month_end":    int(d.is_month_end),
            "is_quarter_start":int(d.is_quarter_start),
            "is_quarter_end":  int(d.is_quarter_end),
            "fiscal_year":     fiscal_year(d),
            "fiscal_quarter":  fiscal_quarter(d),
            "year_month":      d.strftime("%Y-%m"),
        })

    df = pd.DataFrame(rows)
    df.to_sql("dim_date", engine, if_exists="replace", index=False)
    log.info(f"dim_date: {len(df):,} rows ({df['year'].min()}–{df['year'].max()})")
    return df


# ─── dim_customer ─────────────────────────────────────────────────────────────

def build_dim_customer(engine):
    log.info("Building dim_customer …")
    df = pd.read_sql("SELECT * FROM stg_customers", engine)

    keep = ["customer_id", "name", "email", "region", "city", "country",
            "segment", "joined_date", "joined_year", "tenure_days",
            "loyalty_score", "is_active"]
    df = df[[c for c in keep if c in df.columns]].copy()

    df.to_sql("dim_customer", engine, if_exists="replace", index=False)
    log.info(f"dim_customer: {len(df):,} rows")
    return df


# ─── dim_product ──────────────────────────────────────────────────────────────

def build_dim_product(engine):
    log.info("Building dim_product …")
    df = pd.read_sql("SELECT * FROM stg_products", engine)

    keep = ["product_id", "name", "category", "sub_category",
            "unit_cost", "unit_price", "margin_pct", "price_band", "is_active"]
    df = df[[c for c in keep if c in df.columns]].copy()
    df["price_band"] = df["price_band"].astype(str).replace("nan", "Unknown")

    df.to_sql("dim_product", engine, if_exists="replace", index=False)
    log.info(f"dim_product: {len(df):,} rows across {df['category'].nunique()} categories")
    return df


# ─── dim_campaign ─────────────────────────────────────────────────────────────

def build_dim_campaign(engine):
    log.info("Building dim_campaign …")
    df = pd.read_sql("SELECT * FROM stg_campaigns", engine)

    keep = ["campaign_id", "name", "type", "goal",
            "start_date", "end_date", "duration_days", "budget", "status"]
    df = df[[c for c in keep if c in df.columns]].copy()
    for col in ["start_date", "end_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    df.to_sql("dim_campaign", engine, if_exists="replace", index=False)
    log.info(f"dim_campaign: {len(df):,} rows")
    return df


# ─── fact_sales ───────────────────────────────────────────────────────────────

def build_fact_sales(engine):
    log.info("Building fact_sales …")

    # Load staging tables
    orders  = pd.read_sql("SELECT * FROM stg_orders",      engine)
    items   = pd.read_sql("SELECT * FROM stg_order_items", engine)
    prods   = pd.read_sql("SELECT product_id, unit_cost FROM stg_products", engine)

    # Load dimension keys
    dim_cust = pd.read_sql("SELECT rowid AS customer_key, customer_id FROM dim_customer", engine)
    dim_prod = pd.read_sql("SELECT rowid AS product_key,  product_id  FROM dim_product",  engine)
    dim_date = pd.read_sql("SELECT date_key, full_date FROM dim_date", engine)

    # ── Join order items → orders ──────────────────────────────────────────────
    fact = items.merge(
        orders[["order_id", "customer_id", "order_date", "status",
                "channel", "payment_method", "is_revenue"]],
        on="order_id", how="left"
    )

    # ── Attach unit_cost from products ────────────────────────────────────────
    fact = fact.merge(prods, on="product_id", how="left")

    # ── Resolve date_key ──────────────────────────────────────────────────────
    fact["order_date_str"] = pd.to_datetime(
        fact["order_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    fact = fact.merge(dim_date, left_on="order_date_str", right_on="full_date", how="left")

    # ── Resolve customer_key ──────────────────────────────────────────────────
    fact = fact.merge(dim_cust, on="customer_id", how="left")

    # ── Resolve product_key ───────────────────────────────────────────────────
    fact = fact.merge(dim_prod, on="product_id", how="left")

    # ── Assign campaign_key randomly for ~40% of completed orders (demo) ──────
    camp_keys = pd.read_sql("SELECT rowid AS campaign_key FROM dim_campaign", engine)["campaign_key"].tolist()
    np.random.seed(42)
    mask = (fact["status"] == "Completed") & (np.random.rand(len(fact)) < 0.40)
    fact["campaign_key"] = None
    fact.loc[mask, "campaign_key"] = np.random.choice(camp_keys, mask.sum())

    # ── Calculated measures ───────────────────────────────────────────────────
    fact["unit_cost"]       = pd.to_numeric(fact["unit_cost"],    errors="coerce").fillna(0)
    fact["quantity"]        = pd.to_numeric(fact["quantity"],     errors="coerce").fillna(1).astype(int)
    fact["unit_price"]      = pd.to_numeric(fact["unit_price"],   errors="coerce").fillna(0)
    fact["discount_pct"]    = pd.to_numeric(fact["discount_pct"], errors="coerce").fillna(0)
    fact["discount_amt"]    = pd.to_numeric(fact["discount_amt"], errors="coerce").fillna(0)
    fact["line_revenue"]    = pd.to_numeric(fact["line_total"],   errors="coerce").fillna(0)

    fact["line_cost"]       = (fact["unit_cost"] * fact["quantity"]).round(2)
    fact["line_profit"]     = (fact["line_revenue"] - fact["line_cost"]).round(2)
    fact["line_margin_pct"] = np.where(
        fact["line_revenue"] > 0,
        (fact["line_profit"] / fact["line_revenue"] * 100).round(1),
        0
    )

    # Zero out revenue for non-completed orders
    fact["is_revenue"] = fact["is_revenue"].fillna(0).astype(int)
    for col in ["line_revenue", "line_cost", "line_profit", "line_margin_pct"]:
        fact.loc[fact["is_revenue"] == 0, col] = 0

    # ── Select final columns ──────────────────────────────────────────────────
    out = fact[[
        "date_key", "customer_key", "product_key", "campaign_key",
        "order_id", "item_id", "channel", "payment_method", "status",
        "quantity", "unit_price", "unit_cost",
        "discount_pct", "discount_amt",
        "line_revenue", "line_cost", "line_profit", "line_margin_pct",
        "is_revenue",
    ]].rename(columns={"status": "order_status"})

    out = out.dropna(subset=["date_key", "customer_key", "product_key"])
    out["date_key"]     = out["date_key"].astype(int)
    out["customer_key"] = out["customer_key"].astype(int)
    out["product_key"]  = out["product_key"].astype(int)

    out.to_sql("fact_sales", engine, if_exists="replace", index=False)

    completed  = out[out["is_revenue"] == 1]
    total_rev  = completed["line_revenue"].sum()
    total_prof = completed["line_profit"].sum()
    log.info(f"fact_sales: {len(out):,} rows")
    log.info(f"  Revenue rows : {len(completed):,}")
    log.info(f"  Total revenue: ₹{total_rev:,.0f}")
    log.info(f"  Total profit : ₹{total_prof:,.0f}")
    log.info(f"  Avg margin   : {(total_prof/total_rev*100):.1f}%")
    return out


# ─── Rebuild indexes ──────────────────────────────────────────────────────────

def rebuild_indexes(engine):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_fact_date     ON fact_sales(date_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_product  ON fact_sales(product_key)",
        "CREATE INDEX IF NOT EXISTS idx_fact_order    ON fact_sales(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_status   ON fact_sales(order_status)",
        "CREATE INDEX IF NOT EXISTS idx_dim_date_ym   ON dim_date(year_month)",
        "CREATE INDEX IF NOT EXISTS idx_dim_date_year ON dim_date(year)",
    ]
    with engine.connect() as conn:
        for idx in indexes:
            conn.execute(text(idx))
        conn.commit()
    log.info(f"Rebuilt {len(indexes)} indexes")


# ─── Row count summary ────────────────────────────────────────────────────────

def print_summary(engine):
    log.info("─── WAREHOUSE SUMMARY ───────────────────────────────────")
    tables = ["dim_date", "dim_customer", "dim_product", "dim_campaign", "fact_sales"]
    total  = 0
    with engine.connect() as conn:
        for tbl in tables:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            total += n
            tag = "FACT" if tbl.startswith("fact") else "DIM "
            log.info(f"  [{tag}] {tbl:20s}  {n:>7,} rows")
    log.info(f"  {'TOTAL':26s}  {total:>7,} rows")
    log.info("─────────────────────────────────────────────────────────")


# ─── Main ─────────────────────────────────────────────────────────────────────

def build_all():
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║     DATA WAREHOUSE BUILD — DAY 2                        ║")
    log.info("╚══════════════════════════════════════════════════════════╝")

    engine = get_engine()

    log.info("━━━ STEP 1: Create schema ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    create_schema(engine)

    log.info("━━━ STEP 2: Build dimensions ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    build_dim_date(engine)
    build_dim_customer(engine)
    build_dim_product(engine)
    build_dim_campaign(engine)

    log.info("━━━ STEP 3: Build fact table ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    build_fact_sales(engine)

    log.info("━━━ STEP 4: Rebuild indexes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    rebuild_indexes(engine)

    print_summary(engine)
    log.info("Warehouse build complete ✓")


if __name__ == "__main__":
    build_all()
