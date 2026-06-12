"""
tests/test_dashboard.py — API tests for the Flask dashboard (Day 3).

Run: python -m pytest tests/test_dashboard.py -v
"""

import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))


@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def jget(client, url):
    r = client.get(url)
    assert r.status_code == 200, f"{url} returned {r.status_code}"
    return json.loads(r.data)


# ── Page ──────────────────────────────────────────────────────────────────────

class TestPages:
    def test_index_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_index_contains_plotly(self, client):
        r = client.get("/")
        assert b"plotly" in r.data.lower()

    def test_index_contains_nav(self, client):
        r = client.get("/")
        assert b"sidebar" in r.data.lower()


# ── KPIs ──────────────────────────────────────────────────────────────────────

class TestKPIs:
    def test_kpi_endpoint_returns_200(self, client):
        jget(client, "/api/kpis")

    def test_kpi_has_required_fields(self, client):
        d = jget(client, "/api/kpis")
        for field in ["total_revenue","total_profit","total_orders",
                      "unique_customers","avg_margin","avg_order_value","yoy_growth"]:
            assert field in d, f"Missing field: {field}"

    def test_kpi_revenue_positive(self, client):
        d = jget(client, "/api/kpis")
        assert d["total_revenue"] > 0
        assert d["total_profit"] > 0

    def test_kpi_profit_less_than_revenue(self, client):
        d = jget(client, "/api/kpis")
        assert d["total_profit"] < d["total_revenue"]

    def test_kpi_margin_reasonable(self, client):
        d = jget(client, "/api/kpis")
        assert 0 < d["avg_margin"] < 100

    def test_kpi_orders_positive(self, client):
        d = jget(client, "/api/kpis")
        assert d["total_orders"] > 0
        assert d["unique_customers"] > 0


# ── Revenue Routes ────────────────────────────────────────────────────────────

class TestRevenueRoutes:
    def test_monthly_has_36_rows(self, client):
        d = jget(client, "/api/revenue/monthly")
        assert len(d) == 36

    def test_monthly_has_required_fields(self, client):
        d = jget(client, "/api/revenue/monthly")
        row = d[0]
        for f in ["year_month","year","month_name","revenue","profit","total_orders"]:
            assert f in row

    def test_monthly_revenue_all_positive(self, client):
        d = jget(client, "/api/revenue/monthly")
        assert all(r["revenue"] >= 0 for r in d)

    def test_yoy_has_12_rows(self, client):
        d = jget(client, "/api/revenue/yoy")
        assert len(d) == 12

    def test_yoy_has_three_year_columns(self, client):
        d = jget(client, "/api/revenue/yoy")
        row = d[0]
        for col in ["revenue_2022","revenue_2023","revenue_2024"]:
            assert col in row

    def test_region_has_4_rows(self, client):
        d = jget(client, "/api/revenue/region")
        assert len(d) == 4

    def test_region_names_valid(self, client):
        d = jget(client, "/api/revenue/region")
        names = {r["region"] for r in d}
        assert names == {"North","South","East","West"}

    def test_segment_has_4_rows(self, client):
        d = jget(client, "/api/revenue/segment")
        assert len(d) == 4

    def test_channel_has_4_rows(self, client):
        d = jget(client, "/api/revenue/channel")
        assert len(d) == 4


# ── Product Routes ────────────────────────────────────────────────────────────

class TestProductRoutes:
    def test_top_products_returns_15(self, client):
        d = jget(client, "/api/products/top")
        assert len(d) == 15

    def test_top_products_sorted_by_revenue(self, client):
        d = jget(client, "/api/products/top")
        revenues = [r["revenue"] for r in d]
        assert revenues == sorted(revenues, reverse=True)

    def test_top_products_required_fields(self, client):
        d = jget(client, "/api/products/top")
        row = d[0]
        for f in ["product_name","category","revenue","profit","margin","units"]:
            assert f in row

    def test_category_has_5_rows(self, client):
        d = jget(client, "/api/products/category")
        assert len(d) == 5

    def test_category_names_valid(self, client):
        d = jget(client, "/api/products/category")
        names = {r["category"] for r in d}
        assert "Electronics" in names
        assert "Software" in names


# ── Customer Routes ───────────────────────────────────────────────────────────

class TestCustomerRoutes:
    def test_ltv_returns_tiers_and_top10(self, client):
        d = jget(client, "/api/customers/ltv")
        assert "tiers" in d
        assert "top10" in d

    def test_ltv_tiers_count(self, client):
        d = jget(client, "/api/customers/ltv")
        assert len(d["tiers"]) == 4

    def test_ltv_tier_names_valid(self, client):
        d = jget(client, "/api/customers/ltv")
        names = {t["ltv_tier"] for t in d["tiers"]}
        assert names == {"Platinum","Gold","Silver","Bronze"}

    def test_ltv_top10_count(self, client):
        d = jget(client, "/api/customers/ltv")
        assert len(d["top10"]) == 10

    def test_cohort_returns_records(self, client):
        d = jget(client, "/api/customers/cohort")
        assert len(d) > 0

    def test_cohort_has_required_fields(self, client):
        d = jget(client, "/api/customers/cohort")
        row = d[0]
        for f in ["cohort_month","activity_month","active_customers","revenue"]:
            assert f in row


# ── Campaign Routes ───────────────────────────────────────────────────────────

class TestCampaignRoutes:
    def test_campaigns_returns_20(self, client):
        d = jget(client, "/api/campaigns/roi")
        assert len(d) == 20

    def test_campaigns_required_fields(self, client):
        d = jget(client, "/api/campaigns/roi")
        row = d[0]
        for f in ["campaign_name","campaign_type","budget","revenue","roi_pct"]:
            assert f in row

    def test_campaigns_revenue_non_negative(self, client):
        d = jget(client, "/api/campaigns/roi")
        assert all(r["revenue"] >= 0 for r in d)

    def test_campaigns_sorted_by_revenue(self, client):
        d = jget(client, "/api/campaigns/roi")
        revenues = [r["revenue"] for r in d]
        assert revenues == sorted(revenues, reverse=True)
