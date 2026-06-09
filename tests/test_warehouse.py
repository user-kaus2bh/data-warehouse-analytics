"""
tests/test_warehouse.py — Unit + integration tests for Day 2.

Run: python -m pytest tests/test_warehouse.py -v
"""

import sys
import pytest
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))
sys.path.insert(0, str(Path(__file__).parent.parent / "warehouse"))


@pytest.fixture(scope="module")
def engine():
    from config import DB_URL
    return create_engine(DB_URL, echo=False)


# ─── Schema tests ─────────────────────────────────────────────────────────────

class TestSchema:
    def test_all_dim_tables_exist(self, engine):
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        for t in ["dim_date", "dim_customer", "dim_product", "dim_campaign"]:
            assert t in tables, f"Missing table: {t}"

    def test_fact_table_exists(self, engine):
        inspector = inspect(engine)
        assert "fact_sales" in inspector.get_table_names()

    def test_all_kpi_views_exist(self, engine):
        views = [
            "vw_monthly_revenue", "vw_revenue_by_region", "vw_revenue_by_segment",
            "vw_top_products", "vw_category_performance", "vw_campaign_roi",
            "vw_customer_ltv", "vw_cohort_monthly", "vw_channel_performance",
            "vw_yoy_comparison",
        ]
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='view'")
            ).fetchall()
        existing_names = {r[0] for r in existing}
        for v in views:
            assert v in existing_names, f"Missing view: {v}"


# ─── dim_date tests ───────────────────────────────────────────────────────────

class TestDimDate:
    def test_row_count(self, engine):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM dim_date")).scalar()
        assert n == 1096, f"Expected 1096 days (2022–2024), got {n}"

    def test_no_duplicate_date_keys(self, engine):
        with engine.connect() as conn:
            dups = conn.execute(text(
                "SELECT COUNT(*) FROM (SELECT date_key, COUNT(*) c FROM dim_date GROUP BY date_key HAVING c > 1)"
            )).scalar()
        assert dups == 0

    def test_date_range(self, engine):
        df = pd.read_sql("SELECT MIN(full_date) AS mn, MAX(full_date) AS mx FROM dim_date", engine)
        assert df.iloc[0]["mn"] == "2022-01-01"
        assert df.iloc[0]["mx"] == "2024-12-31"

    def test_weekend_flag(self, engine):
        df = pd.read_sql(
            "SELECT day_name, is_weekend FROM dim_date WHERE full_date = '2024-01-06'", engine
        )  # 2024-01-06 is a Saturday
        assert df.iloc[0]["is_weekend"] == 1

    def test_fiscal_year_logic(self, engine):
        # April 2023 → fiscal year 2023
        df = pd.read_sql(
            "SELECT fiscal_year, fiscal_quarter FROM dim_date WHERE full_date = '2023-04-01'", engine
        )
        assert df.iloc[0]["fiscal_year"] == 2023
        assert df.iloc[0]["fiscal_quarter"] == 1

    def test_year_month_format(self, engine):
        df = pd.read_sql(
            "SELECT year_month FROM dim_date WHERE full_date = '2023-06-15'", engine
        )
        assert df.iloc[0]["year_month"] == "2023-06"


# ─── dim_customer tests ───────────────────────────────────────────────────────

class TestDimCustomer:
    def test_row_count(self, engine):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM dim_customer")).scalar()
        assert n == 500

    def test_required_columns(self, engine):
        df = pd.read_sql("SELECT * FROM dim_customer LIMIT 1", engine)
        for col in ["customer_id", "name", "region", "segment"]:
            assert col in df.columns

    def test_no_null_customer_ids(self, engine):
        with engine.connect() as conn:
            nulls = conn.execute(
                text("SELECT COUNT(*) FROM dim_customer WHERE customer_id IS NULL")
            ).scalar()
        assert nulls == 0

    def test_valid_segments(self, engine):
        df = pd.read_sql("SELECT DISTINCT segment FROM dim_customer", engine)
        valid = {"Enterprise", "Smb", "Startup", "Consumer", "SMB"}
        for seg in df["segment"]:
            assert seg in valid, f"Unexpected segment: {seg}"


# ─── dim_product tests ────────────────────────────────────────────────────────

class TestDimProduct:
    def test_row_count(self, engine):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM dim_product")).scalar()
        assert n == 50

    def test_five_categories(self, engine):
        with engine.connect() as conn:
            n = conn.execute(
                text("SELECT COUNT(DISTINCT category) FROM dim_product")
            ).scalar()
        assert n == 5

    def test_positive_prices(self, engine):
        with engine.connect() as conn:
            bad = conn.execute(
                text("SELECT COUNT(*) FROM dim_product WHERE unit_price <= 0")
            ).scalar()
        assert bad == 0

    def test_price_greater_than_cost(self, engine):
        df = pd.read_sql("SELECT unit_price, unit_cost FROM dim_product", engine)
        assert (df["unit_price"] > df["unit_cost"]).all()


# ─── fact_sales tests ─────────────────────────────────────────────────────────

class TestFactSales:
    def test_row_count(self, engine):
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
        assert n == 10528

    def test_no_null_foreign_keys(self, engine):
        with engine.connect() as conn:
            for fk in ["date_key", "customer_key", "product_key"]:
                nulls = conn.execute(
                    text(f"SELECT COUNT(*) FROM fact_sales WHERE {fk} IS NULL")
                ).scalar()
                assert nulls == 0, f"Null {fk} in fact_sales: {nulls} rows"

    def test_all_date_keys_exist_in_dim(self, engine):
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_date d ON f.date_key = d.date_key
                WHERE d.date_key IS NULL
            """)).scalar()
        assert orphans == 0

    def test_all_customer_keys_exist_in_dim(self, engine):
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_customer c ON f.customer_key = c.rowid
                WHERE c.rowid IS NULL
            """)).scalar()
        assert orphans == 0

    def test_all_product_keys_exist_in_dim(self, engine):
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_product p ON f.product_key = p.rowid
                WHERE p.rowid IS NULL
            """)).scalar()
        assert orphans == 0

    def test_revenue_rows_have_positive_revenue(self, engine):
        with engine.connect() as conn:
            bad = conn.execute(text("""
                SELECT COUNT(*) FROM fact_sales
                WHERE is_revenue = 1 AND line_revenue <= 0
            """)).scalar()
        assert bad == 0

    def test_non_revenue_rows_have_zero_revenue(self, engine):
        with engine.connect() as conn:
            bad = conn.execute(text("""
                SELECT COUNT(*) FROM fact_sales
                WHERE is_revenue = 0 AND line_revenue > 0
            """)).scalar()
        assert bad == 0

    def test_profit_equals_revenue_minus_cost(self, engine):
        df = pd.read_sql("""
            SELECT line_revenue, line_cost, line_profit FROM fact_sales
            WHERE is_revenue = 1 LIMIT 500
        """, engine)
        calc = (df["line_revenue"] - df["line_cost"]).round(1)
        actual = df["line_profit"].round(1)
        assert (abs(calc - actual) < 1.0).all()


# ─── KPI View tests ───────────────────────────────────────────────────────────

class TestKPIViews:
    def test_monthly_revenue_36_rows(self, engine):
        df = pd.read_sql("SELECT * FROM vw_monthly_revenue", engine)
        assert len(df) == 36, f"Expected 36 months (3 years), got {len(df)}"

    def test_monthly_revenue_non_negative(self, engine):
        df = pd.read_sql("SELECT total_revenue FROM vw_monthly_revenue", engine)
        assert (df["total_revenue"] >= 0).all()

    def test_yoy_has_12_rows(self, engine):
        df = pd.read_sql("SELECT * FROM vw_yoy_comparison", engine)
        assert len(df) == 12

    def test_top_products_ordered_by_revenue(self, engine):
        df = pd.read_sql("SELECT total_revenue FROM vw_top_products", engine)
        assert list(df["total_revenue"]) == sorted(df["total_revenue"].tolist(), reverse=True)

    def test_customer_ltv_tiers_valid(self, engine):
        df = pd.read_sql("SELECT DISTINCT ltv_tier FROM vw_customer_ltv", engine)
        valid = {"Platinum", "Gold", "Silver", "Bronze"}
        assert set(df["ltv_tier"]).issubset(valid)

    def test_campaign_roi_positive_revenue(self, engine):
        df = pd.read_sql("SELECT attributed_revenue FROM vw_campaign_roi", engine)
        assert (df["attributed_revenue"] >= 0).all()

    def test_cohort_view_non_empty(self, engine):
        df = pd.read_sql("SELECT COUNT(*) AS n FROM vw_cohort_monthly", engine)
        assert df.iloc[0]["n"] > 0

    def test_region_view_has_4_regions(self, engine):
        df = pd.read_sql(
            "SELECT COUNT(DISTINCT region) AS n FROM vw_revenue_by_region", engine
        )
        assert df.iloc[0]["n"] == 4
