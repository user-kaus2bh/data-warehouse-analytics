"""
test_etl.py — Unit tests for the ETL pipeline (Day 1).

Run with:  python -m pytest tests/test_etl.py -v
"""

import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_customers():
    return pd.DataFrame({
        "customer_id": ["CUST00001", "CUST00002", "CUST00001"],  # one dup
        "name":        ["alice smith", "BOB JONES", "alice smith"],
        "email":       ["Alice@EXAMPLE.COM", "bob@example.com", "Alice@EXAMPLE.COM"],
        "region":      ["north", "South", "north"],
        "segment":     ["enterprise", "SMB", "enterprise"],
        "joined_date": ["2022-01-15", "2023-06-20", "2022-01-15"],
        "is_active":   [1, None, 1],
        "phone":       ["9999", "8888", "9999"],
        "city":        ["Delhi", "Mumbai", "Delhi"],
        "country":     ["India", "India", "India"],
        "loyalty_score": [8.5, 7.2, 8.5],
    })


@pytest.fixture
def sample_products():
    return pd.DataFrame({
        "product_id":   ["PROD0001", "PROD0002"],
        "name":         ["Laptop Pro", "Notebook"],
        "category":     ["electronics", "stationery"],
        "unit_cost":    [30000.0, 50.0],
        "unit_price":   [55000.0, 99.0],
        "margin_pct":   [45.4, 49.5],
        "stock_qty":    [100, 200],
        "is_active":    [1, 1],
        "sub_category": ["electronics", "stationery"],
        "launch_date":  ["2021-01-01", "2020-06-15"],
    })


@pytest.fixture
def sample_orders():
    return pd.DataFrame({
        "order_id":       ["ORD0000001", "ORD0000002", "ORD0000003"],
        "customer_id":    ["CUST00001", "CUST00002", "CUST00001"],
        "order_date":     ["2023-01-10", "2023-03-15", "bad-date"],
        "shipped_date":   ["2023-01-12", None, "2023-03-17"],
        "status":         ["Completed", "Cancelled", "INVALID_STATUS"],
        "channel":        ["Online", "Partner", "Direct"],
        "payment_method": ["UPI", "Credit Card", "Cash"],
        "order_total":    [50000.0, 0.0, 1200.0],
        "order_profit":   [15000.0, 0.0, 400.0],
        "num_items":      [2, 1, 1],
    })


# ─── Transform tests ──────────────────────────────────────────────────────────

class TestTransformCustomers:
    def test_deduplication(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert len(result) == 2, "Should remove 1 duplicate customer"

    def test_email_lowercase(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert all(result["email"] == result["email"].str.lower())

    def test_name_titlecase(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert "Alice Smith" in result["name"].values

    def test_is_active_filled(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert result["is_active"].isna().sum() == 0

    def test_tenure_days_non_negative(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert (result["tenure_days"] >= 0).all()

    def test_joined_year_extracted(self, sample_customers):
        from transform import transform_customers
        result = transform_customers(sample_customers)
        assert "joined_year" in result.columns
        assert set(result["joined_year"].dropna().astype(int)).issubset({2022, 2023})


class TestTransformProducts:
    def test_margin_recalculated(self, sample_products):
        from transform import transform_products
        result = transform_products(sample_products)
        expected = round((55000 - 30000) / 55000 * 100, 1)
        assert abs(result.iloc[0]["margin_pct"] - expected) < 0.2

    def test_price_band_assigned(self, sample_products):
        from transform import transform_products
        result = transform_products(sample_products)
        assert "price_band" in result.columns
        assert result.iloc[0]["price_band"] == "Enterprise"  # 55000 in Enterprise band (20k-100k)

    def test_category_titlecase(self, sample_products):
        from transform import transform_products
        result = transform_products(sample_products)
        assert result.iloc[0]["category"] == "Electronics"


class TestTransformOrders:
    def test_bad_date_becomes_nat(self, sample_orders):
        from transform import transform_orders
        result = transform_orders(sample_orders)
        nat_count = result["order_date"].isna().sum()
        assert nat_count == 1, "One bad date should become NaT"

    def test_invalid_status_replaced(self, sample_orders):
        from transform import transform_orders
        result = transform_orders(sample_orders)
        assert "INVALID_STATUS" not in result["status"].values
        assert "Unknown" in result["status"].values

    def test_date_parts_derived(self, sample_orders):
        from transform import transform_orders
        result = transform_orders(sample_orders)
        for col in ["order_year", "order_month", "order_quarter"]:
            assert col in result.columns

    def test_is_revenue_flag(self, sample_orders):
        from transform import transform_orders
        result = transform_orders(sample_orders)
        completed = result[result["status"] == "Completed"]
        assert (completed["is_revenue"] == 1).all()
        cancelled = result[result["status"] == "Cancelled"]
        assert (cancelled["is_revenue"] == 0).all()


# ─── Extract tests ────────────────────────────────────────────────────────────

class TestExtract:
    def test_extract_returns_all_sources(self):
        from extract import extract_all
        data = extract_all()
        assert set(data.keys()) == {"customers", "products", "orders", "order_items", "campaigns"}

    def test_row_counts_reasonable(self):
        from extract import extract_all
        data = extract_all()
        assert len(data["customers"]) >= 100
        assert len(data["orders"])    >= 1000
        assert len(data["order_items"]) > len(data["orders"])  # items > orders

    def test_expected_columns_present(self):
        from extract import extract_all, EXPECTED_COLUMNS
        data = extract_all()
        for source, df in data.items():
            expected = EXPECTED_COLUMNS.get(source, [])
            missing = [c for c in expected if c not in df.columns]
            assert len(missing) == 0, f"{source} missing columns: {missing}"


# ─── Integration test ─────────────────────────────────────────────────────────

class TestEndToEnd:
    def test_full_pipeline_runs(self):
        from extract   import extract_all
        from transform import transform_all
        raw     = extract_all()
        cleaned = transform_all(raw)
        assert len(cleaned) == 5
        for name, df in cleaned.items():
            assert len(df) > 0, f"{name} is empty after transform"

    def test_no_negative_revenue(self):
        from extract   import extract_all
        from transform import transform_all
        raw     = extract_all()
        cleaned = transform_all(raw)
        orders = cleaned["orders"]
        completed = orders[orders["status"] == "Completed"]
        assert (completed["order_total"] >= 0).all()

    def test_order_items_reference_valid_orders(self):
        from extract   import extract_all
        from transform import transform_all
        raw     = extract_all()
        cleaned = transform_all(raw)
        order_ids = set(cleaned["orders"]["order_id"])
        item_order_ids = set(cleaned["order_items"]["order_id"])
        orphans = item_order_ids - order_ids
        assert len(orphans) == 0, f"Orphan order_ids in items: {orphans}"
