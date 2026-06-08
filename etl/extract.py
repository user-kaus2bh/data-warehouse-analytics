"""
extract.py — Extraction layer of the ETL pipeline.

Responsibilities:
  - Read raw CSV and JSON files from data/raw/
  - Perform basic schema validation (expected columns present)
  - Return raw DataFrames without modification
  - Log row counts, file sizes, and any read errors
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional

from config import RAW_DATA_DIR
from logger import get_logger

log = get_logger("extract")

# ─── Expected schemas per source ──────────────────────────────────────────────

EXPECTED_COLUMNS = {
    "customers":   ["customer_id", "name", "email", "region", "segment", "joined_date"],
    "products":    ["product_id", "name", "category", "unit_cost", "unit_price"],
    "orders":      ["order_id", "customer_id", "order_date", "status", "order_total"],
    "order_items": ["item_id", "order_id", "product_id", "quantity", "unit_price", "line_total"],
    "campaigns":   ["campaign_id", "name", "type", "start_date", "end_date", "spend", "impressions"],
}


# ─── Core readers ─────────────────────────────────────────────────────────────

def read_csv(filename: str, source_name: str) -> Optional[pd.DataFrame]:
    """Read a CSV file from RAW_DATA_DIR and validate columns."""
    path = RAW_DATA_DIR / filename
    if not path.exists():
        log.error(f"File not found: {path}")
        return None

    try:
        df = pd.read_csv(path, low_memory=False)
        size_kb = path.stat().st_size / 1024
        log.info(f"Read {source_name}: {len(df):,} rows × {len(df.columns)} cols  ({size_kb:.1f} KB)")

        _validate_columns(df, source_name)
        return df

    except Exception as e:
        log.error(f"Failed to read {filename}: {e}")
        return None


def read_json(filename: str, source_name: str) -> Optional[pd.DataFrame]:
    """Read a JSON array file and return as DataFrame."""
    path = RAW_DATA_DIR / filename
    if not path.exists():
        log.error(f"File not found: {path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Support both top-level array and {records: [...]} wrapper
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "records" in data:
            df = pd.DataFrame(data["records"])
        else:
            log.error(f"Unexpected JSON structure in {filename}")
            return None

        size_kb = path.stat().st_size / 1024
        log.info(f"Read {source_name}: {len(df):,} rows × {len(df.columns)} cols  ({size_kb:.1f} KB)")

        _validate_columns(df, source_name)
        return df

    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {filename}: {e}")
        return None
    except Exception as e:
        log.error(f"Failed to read {filename}: {e}")
        return None


def _validate_columns(df: pd.DataFrame, source_name: str):
    """Check that all expected columns are present."""
    expected = EXPECTED_COLUMNS.get(source_name, [])
    missing  = [c for c in expected if c not in df.columns]
    extra    = [c for c in df.columns if c not in expected and expected]

    if missing:
        log.warning(f"{source_name}: missing expected columns: {missing}")
    else:
        log.debug(f"{source_name}: all expected columns present ✓")

    if extra:
        log.debug(f"{source_name}: additional columns found: {extra}")


# ─── Public extraction function ───────────────────────────────────────────────

def extract_all() -> dict[str, pd.DataFrame]:
    """
    Extract all raw source files and return a dict of DataFrames.
    Keys: customers, products, orders, order_items, campaigns
    """
    log.info("─── EXTRACT PHASE ───────────────────────────────────────")

    sources = {
        "customers":   ("customers.csv",   "csv"),
        "products":    ("products.csv",    "csv"),
        "orders":      ("orders.csv",      "csv"),
        "order_items": ("order_items.csv", "csv"),
        "campaigns":   ("campaigns.json",  "json"),
    }

    extracted = {}
    failed    = []

    for name, (filename, fmt) in sources.items():
        if fmt == "csv":
            df = read_csv(filename, name)
        else:
            df = read_json(filename, name)

        if df is not None:
            extracted[name] = df
        else:
            failed.append(name)

    log.info(f"Extracted {len(extracted)}/{len(sources)} sources successfully")
    if failed:
        log.warning(f"Failed sources: {failed}")

    return extracted


# ─── Entry point for standalone testing ───────────────────────────────────────

if __name__ == "__main__":
    data = extract_all()
    print("\nExtracted sources:")
    for name, df in data.items():
        print(f"  {name:15s}  {len(df):>6,} rows")
