"""
load.py — Load layer of the ETL pipeline.

Responsibilities:
  - Create staging tables in SQLite (schema auto-created from DataFrames)
  - Load each cleaned DataFrame into its staging table
  - Implement upsert logic (replace on re-runs)
  - Verify row counts post-load
  - Print a final load summary
"""

import pandas as pd
from sqlalchemy import create_engine, text, inspect, String
from sqlalchemy.exc import SQLAlchemyError

from config import DB_URL, DB_PATH
from logger import get_logger

log = get_logger("load")


# ─── Table name mapping ───────────────────────────────────────────────────────

STAGING_TABLES = {
    "customers":   "stg_customers",
    "products":    "stg_products",
    "orders":      "stg_orders",
    "order_items": "stg_order_items",
    "campaigns":   "stg_campaigns",
}


# ─── Dtype hints for SQLite/Pandas compatibility ──────────────────────────────

DTYPE_OVERRIDES = {
    "stg_customers": {
        "joined_date": String(),
    },
    "stg_orders": {
        "order_date":   String(),
        "shipped_date": String(),
    },
    "stg_campaigns": {
        "start_date": String(),
        "end_date":   String(),
    },
}


# ─── Core loader ─────────────────────────────────────────────────────────────

def get_engine():
    """Create and return a SQLAlchemy engine."""
    engine = create_engine(DB_URL, echo=False)
    return engine


def load_table(
    df: pd.DataFrame,
    table_name: str,
    engine,
    if_exists: str = "replace",
) -> int:
    """
    Load a DataFrame into a database table.
    Returns the number of rows written.
    """
    # Convert any remaining Timestamps/Categoricals to strings for SQLite compat
    df_clean = df.copy()
    for col in df_clean.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df_clean[col] = df_clean[col].dt.strftime("%Y-%m-%d").where(df_clean[col].notna(), None)
    for col in df_clean.select_dtypes(include=["category"]).columns:
        df_clean[col] = df_clean[col].astype(str)

    dtype_map = DTYPE_OVERRIDES.get(table_name, {})

    try:
        df_clean.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False,
            dtype=dtype_map or None,
            chunksize=1000,     # stream in chunks for large tables
            method="multi",
        )
        # Verify
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
        log.info(f"Loaded {table_name:20s}  {count:>7,} rows  ✓")
        return count

    except SQLAlchemyError as e:
        log.error(f"Failed to load {table_name}: {e}")
        return -1


# ─── Post-load verification ───────────────────────────────────────────────────

def verify_staging(engine):
    """Cross-check row counts and log referential integrity."""
    log.info("─── STAGING VERIFICATION ────────────────────────────────")
    inspector = inspect(engine)
    tables    = inspector.get_table_names()

    with engine.connect() as conn:
        for tbl in sorted(tables):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            log.info(f"  {tbl:25s}  {count:>7,} rows")

        # Referential checks
        log.info("Referential integrity checks:")
        checks = [
            (
                "Orders → Customers",
                "SELECT COUNT(*) FROM stg_orders o "
                "LEFT JOIN stg_customers c USING (customer_id) "
                "WHERE c.customer_id IS NULL"
            ),
            (
                "Order items → Orders",
                "SELECT COUNT(*) FROM stg_order_items oi "
                "LEFT JOIN stg_orders o USING (order_id) "
                "WHERE o.order_id IS NULL"
            ),
            (
                "Order items → Products",
                "SELECT COUNT(*) FROM stg_order_items oi "
                "LEFT JOIN stg_products p USING (product_id) "
                "WHERE p.product_id IS NULL"
            ),
        ]
        for label, sql in checks:
            orphans = conn.execute(text(sql)).scalar()
            status  = "✓ OK" if orphans == 0 else f"⚠ {orphans} orphans"
            log.info(f"  {label:30s}  {status}")

    log.info("──────────────────────────────────────────────────────────")


# ─── Public orchestrator ──────────────────────────────────────────────────────

def load_all(cleaned: dict[str, pd.DataFrame]) -> dict[str, int]:
    """
    Load all cleaned DataFrames into staging tables.
    Returns a dict of {table_name: row_count}.
    """
    log.info("─── LOAD PHASE ──────────────────────────────────────────")
    log.info(f"Target database: {DB_URL}")

    engine = get_engine()
    results = {}

    for source_name, table_name in STAGING_TABLES.items():
        if source_name not in cleaned:
            log.warning(f"'{source_name}' not in cleaned data — skipping load")
            continue

        df = cleaned[source_name]
        rows = load_table(df, table_name, engine)
        results[table_name] = rows

    verify_staging(engine)

    total = sum(r for r in results.values() if r >= 0)
    log.info(f"Load phase complete — {total:,} total rows across {len(results)} tables")
    return results


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from extract   import extract_all
    from transform import transform_all

    raw     = extract_all()
    cleaned = transform_all(raw)
    results = load_all(cleaned)

    print(f"\nDB written to: {DB_PATH}")
    print(f"Tables loaded: {len(results)}")
    for tbl, cnt in results.items():
        print(f"  {tbl:25s}  {cnt:>7,} rows")
