"""
transform.py — Transformation layer of the ETL pipeline.

Responsibilities:
  - Clean nulls, fix data types, standardize formats
  - Deduplicate records
  - Derive new columns (age buckets, revenue bands, date parts)
  - Apply business rules (flag anomalies, compute margins)
  - Return fully cleaned DataFrames ready for loading
  - Emit data quality report at end
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from config import PROCESSED_DATA_DIR
from logger import get_logger

log = get_logger("transform")

TODAY = pd.Timestamp.now().normalize()


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _safe_to_datetime(series: pd.Series, col_name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    bad = parsed.isna().sum()
    if bad:
        log.warning(f"{col_name}: {bad} unparseable dates → NaT")
    return parsed


def _null_report(df: pd.DataFrame, name: str):
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        log.debug(f"{name}: no nulls ✓")
    else:
        for col, cnt in nulls.items():
            pct = cnt / len(df) * 100
            log.warning(f"{name}.{col}: {cnt} nulls ({pct:.1f}%)")


def _dedup(df: pd.DataFrame, id_col: str, name: str) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=[id_col])
    removed = before - len(df)
    if removed:
        log.warning(f"{name}: removed {removed} duplicate {id_col}s")
    else:
        log.debug(f"{name}: no duplicates found ✓")
    return df


# ─── Customers ────────────────────────────────────────────────────────────────

def transform_customers(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Transforming customers …")
    df = df.copy()

    # Types & cleaning
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    df["name"]        = df["name"].astype(str).str.strip().str.title()
    df["email"]       = df["email"].astype(str).str.strip().str.lower()
    df["region"]      = df["region"].astype(str).str.strip().str.title()
    df["segment"]     = df["segment"].astype(str).str.strip().str.title()
    df["is_active"]   = df["is_active"].fillna(1).astype(int)

    # Dates
    df["joined_date"] = _safe_to_datetime(df["joined_date"], "joined_date")
    df["joined_year"] = df["joined_date"].dt.year
    df["joined_month"]= df["joined_date"].dt.month

    # Derived: tenure in days
    df["tenure_days"] = (TODAY - df["joined_date"]).dt.days.clip(lower=0)

    # Deduplicate
    df = _dedup(df, "customer_id", "customers")
    _null_report(df, "customers")

    log.info(f"Customers transformed: {len(df):,} rows")
    return df


# ─── Products ─────────────────────────────────────────────────────────────────

def transform_products(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Transforming products …")
    df = df.copy()

    # Numeric coercion
    df["unit_cost"]  = pd.to_numeric(df["unit_cost"],  errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    # Fill missing prices with cost × 1.5 (fallback)
    mask = df["unit_price"].isna()
    df.loc[mask, "unit_price"] = (df.loc[mask, "unit_cost"] * 1.5).round(2)
    if mask.sum():
        log.warning(f"products: filled {mask.sum()} missing unit_prices with cost × 1.5")

    # Recalculate margin (source may have stale value)
    df["margin_pct"] = ((df["unit_price"] - df["unit_cost"]) / df["unit_price"] * 100).round(1)

    # Price bands for analytics
    df["price_band"] = pd.cut(
        df["unit_price"],
        bins=[0, 1000, 5000, 20000, 100000, float("inf")],
        labels=["Budget", "Mid-Range", "Premium", "Enterprise", "Luxury"],
    )

    # Standardize text
    df["category"]    = df["category"].str.strip().str.title()
    df["is_active"]   = df["is_active"].fillna(1).astype(int)

    # Negative cost/price guard
    bad_price = df["unit_price"] <= 0
    if bad_price.sum():
        log.warning(f"products: {bad_price.sum()} rows have non-positive price — flagged")
        df.loc[bad_price, "is_active"] = 0

    df = _dedup(df, "product_id", "products")
    _null_report(df, "products")

    log.info(f"Products transformed: {len(df):,} rows")
    return df


# ─── Orders ───────────────────────────────────────────────────────────────────

VALID_STATUSES  = {"Completed", "Returned", "Cancelled", "Pending"}
VALID_CHANNELS  = {"Online", "Sales Rep", "Partner", "Direct"}


def transform_orders(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Transforming orders …")
    df = df.copy()

    # Dates
    df["order_date"]   = _safe_to_datetime(df["order_date"],   "order_date")
    df["shipped_date"] = _safe_to_datetime(df["shipped_date"], "shipped_date")

    # Derived date parts (crucial for star schema dim_date join)
    df["order_year"]    = df["order_date"].dt.year
    df["order_month"]   = df["order_date"].dt.month
    df["order_quarter"] = df["order_date"].dt.quarter
    df["order_dow"]     = df["order_date"].dt.day_name()
    df["order_week"]    = df["order_date"].dt.isocalendar().week.astype("Int64")

    # Fulfillment lag (days from order to ship)
    df["fulfillment_days"] = (df["shipped_date"] - df["order_date"]).dt.days
    df.loc[df["fulfillment_days"] < 0, "fulfillment_days"] = np.nan  # bad data guard

    # Numeric coercion
    df["order_total"]  = pd.to_numeric(df["order_total"],  errors="coerce").fillna(0)
    df["order_profit"] = pd.to_numeric(df["order_profit"], errors="coerce").fillna(0)
    df["num_items"]    = pd.to_numeric(df["num_items"],    errors="coerce").fillna(1).astype(int)

    # Standardize categoricals
    df["status"]  = df["status"].str.strip().str.title()
    df["channel"] = df["channel"].str.strip().str.title()

    invalid_status = ~df["status"].isin(VALID_STATUSES)
    if invalid_status.sum():
        log.warning(f"orders: {invalid_status.sum()} unknown statuses → 'Unknown'")
        df.loc[invalid_status, "status"] = "Unknown"

    # Revenue flag: only Completed orders carry revenue
    df["is_revenue"] = (df["status"] == "Completed").astype(int)

    # Anomaly flags
    df["is_high_value"] = (df["order_total"] > df["order_total"].quantile(0.95)).astype(int)
    df["has_zero_total"] = (df["order_total"] == 0).astype(int)

    df = _dedup(df, "order_id", "orders")
    _null_report(df, "orders")

    completed = df[df["status"] == "Completed"]
    log.info(f"Orders transformed: {len(df):,} total, {len(completed):,} completed")
    log.info(f"Revenue orders total: ₹{completed['order_total'].sum():,.0f}")
    return df


# ─── Order Items ──────────────────────────────────────────────────────────────

def transform_order_items(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Transforming order_items …")
    df = df.copy()

    # Numeric coercion
    for col in ["quantity", "unit_price", "discount_pct", "discount_amt", "line_total", "line_profit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["quantity"] = df["quantity"].astype(int).clip(lower=1)

    # Guard: negative line_total
    bad = df["line_total"] < 0
    if bad.sum():
        log.warning(f"order_items: {bad.sum()} negative line_totals → set to 0")
        df.loc[bad, "line_total"] = 0

    # Derived: effective unit price after discount
    df["effective_unit_price"] = (df["unit_price"] - df["discount_amt"]).round(2)

    df = _dedup(df, "item_id", "order_items")
    _null_report(df, "order_items")

    log.info(f"Order items transformed: {len(df):,} rows")
    return df


# ─── Campaigns ────────────────────────────────────────────────────────────────

def transform_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Transforming campaigns …")
    df = df.copy()

    df["start_date"] = _safe_to_datetime(df["start_date"], "start_date")
    df["end_date"]   = _safe_to_datetime(df["end_date"],   "end_date")
    df["duration_days"] = (df["end_date"] - df["start_date"]).dt.days

    for col in ["budget", "spend", "impressions", "clicks", "conversions", "revenue_generated"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["ctr"]              = df["ctr"].round(3)
    df["conversion_rate"]  = df["conversion_rate"].round(3)
    df["roi"]              = df["roi"].round(2)
    df["cost_per_click"]   = (df["spend"] / df["clicks"].replace(0, np.nan)).round(2)
    df["cost_per_conv"]    = (df["spend"] / df["conversions"].replace(0, np.nan)).round(2)
    df["roas"]             = (df["revenue_generated"] / df["spend"].replace(0, np.nan)).round(2)

    df = _dedup(df, "campaign_id", "campaigns")
    _null_report(df, "campaigns")

    log.info(f"Campaigns transformed: {len(df):,} rows")
    return df


# ─── Data Quality Report ──────────────────────────────────────────────────────

def quality_report(datasets: dict[str, pd.DataFrame]):
    log.info("─── DATA QUALITY REPORT ──────────────────────────────────")
    total_rows = 0
    for name, df in datasets.items():
        null_pct   = df.isna().mean().mean() * 100
        dup_count  = df.duplicated().sum()
        total_rows += len(df)
        status = "✓ PASS" if null_pct < 5 and dup_count == 0 else "⚠ CHECK"
        log.info(
            f"  {name:15s}  rows={len(df):>6,}  null%={null_pct:.1f}%  "
            f"dups={dup_count}  {status}"
        )
    log.info(f"  {'TOTAL':15s}  rows={total_rows:>6,}")
    log.info("──────────────────────────────────────────────────────────")


# ─── Public orchestrator ──────────────────────────────────────────────────────

def transform_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    log.info("─── TRANSFORM PHASE ─────────────────────────────────────")

    transformers = {
        "customers":   transform_customers,
        "products":    transform_products,
        "orders":      transform_orders,
        "order_items": transform_order_items,
        "campaigns":   transform_campaigns,
    }

    cleaned = {}
    for name, fn in transformers.items():
        if name in raw:
            cleaned[name] = fn(raw[name])
        else:
            log.warning(f"Source '{name}' not in raw data — skipping transform")

    quality_report(cleaned)

    # Save processed CSVs for inspection
    for name, df in cleaned.items():
        out = PROCESSED_DATA_DIR / f"{name}_clean.csv"
        df.to_csv(out, index=False)
        log.debug(f"Saved processed: {out.name}")

    log.info(f"Transform phase complete — {len(cleaned)} datasets ready")
    return cleaned


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from extract import extract_all
    raw     = extract_all()
    cleaned = transform_all(raw)
    print("\nCleaned datasets:")
    for name, df in cleaned.items():
        print(f"  {name:15s}  {len(df):>6,} rows  {len(df.columns)} columns")
