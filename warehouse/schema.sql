-- ============================================================
-- warehouse/schema.sql
-- Star Schema DDL for the Data Warehouse
--
-- Structure:
--   1 Fact Table  : fact_sales
--   4 Dim Tables  : dim_date, dim_customer, dim_product, dim_campaign
--
-- Naming convention:
--   fact_*  → measures / numbers you want to analyse
--   dim_*   → context / who, what, when, where
-- ============================================================


-- ─── Drop tables if rebuilding ────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_campaign;


-- ─── dim_date ─────────────────────────────────────────────────────────────────
-- One row per calendar day from 2022-01-01 to 2024-12-31
-- Lets us slice facts by any time dimension without string parsing
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,   -- YYYYMMDD integer e.g. 20230615
    full_date       TEXT    NOT NULL,      -- "2023-06-15"
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,      -- 1–4
    month           INTEGER NOT NULL,      -- 1–12
    month_name      TEXT    NOT NULL,      -- "June"
    week            INTEGER NOT NULL,      -- ISO week 1–53
    day_of_month    INTEGER NOT NULL,      -- 1–31
    day_of_week     INTEGER NOT NULL,      -- 1=Monday … 7=Sunday
    day_name        TEXT    NOT NULL,      -- "Thursday"
    is_weekend      INTEGER NOT NULL,      -- 1 if Sat/Sun, else 0
    is_month_start  INTEGER NOT NULL,
    is_month_end    INTEGER NOT NULL,
    is_quarter_start INTEGER NOT NULL,
    is_quarter_end   INTEGER NOT NULL,
    fiscal_year     INTEGER NOT NULL,      -- April–March Indian fiscal year
    fiscal_quarter  INTEGER NOT NULL,
    year_month      TEXT    NOT NULL       -- "2023-06" for easy grouping
);


-- ─── dim_customer ─────────────────────────────────────────────────────────────
CREATE TABLE dim_customer (
    customer_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    email           TEXT,
    region          TEXT    NOT NULL,
    city            TEXT,
    country         TEXT,
    segment         TEXT    NOT NULL,      -- Enterprise / SMB / Startup / Consumer
    joined_date     TEXT,
    joined_year     INTEGER,
    tenure_days     INTEGER,
    loyalty_score   REAL,
    is_active       INTEGER DEFAULT 1
);


-- ─── dim_product ──────────────────────────────────────────────────────────────
CREATE TABLE dim_product (
    product_key     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL,
    sub_category    TEXT,
    unit_cost       REAL    NOT NULL,
    unit_price      REAL    NOT NULL,
    margin_pct      REAL,
    price_band      TEXT,                  -- Budget / Mid-Range / Premium / Enterprise / Luxury
    is_active       INTEGER DEFAULT 1
);


-- ─── dim_campaign ─────────────────────────────────────────────────────────────
CREATE TABLE dim_campaign (
    campaign_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id     TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    type            TEXT    NOT NULL,      -- Email / Social Media / Search Ads / etc.
    goal            TEXT,                  -- Awareness / Lead Gen / Conversion / Retention
    start_date      TEXT,
    end_date        TEXT,
    duration_days   INTEGER,
    budget          REAL,
    status          TEXT
);


-- ─── fact_sales ───────────────────────────────────────────────────────────────
-- Grain: one row per order line item
-- Each row = one product sold on one order
CREATE TABLE fact_sales (
    sale_key        INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign keys to dimensions
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key    INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key     INTEGER NOT NULL REFERENCES dim_product(product_key),
    campaign_key    INTEGER,               -- nullable: not all orders linked to a campaign

    -- Degenerate dimensions (kept in fact for convenience)
    order_id        TEXT    NOT NULL,
    item_id         TEXT    NOT NULL,
    channel         TEXT,
    payment_method  TEXT,
    order_status    TEXT,

    -- Measures
    quantity        INTEGER NOT NULL,
    unit_price      REAL    NOT NULL,
    unit_cost       REAL    NOT NULL,
    discount_pct    REAL    DEFAULT 0,
    discount_amt    REAL    DEFAULT 0,
    line_revenue    REAL    NOT NULL,      -- after discount
    line_cost       REAL    NOT NULL,      -- quantity × unit_cost
    line_profit     REAL    NOT NULL,      -- revenue − cost
    line_margin_pct REAL,                  -- profit / revenue × 100
    is_revenue      INTEGER DEFAULT 1      -- 0 for Cancelled/Returned
);


-- ─── Indexes for common query patterns ────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_fact_date     ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_customer ON fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_product  ON fact_sales(product_key);
CREATE INDEX IF NOT EXISTS idx_fact_order    ON fact_sales(order_id);
CREATE INDEX IF NOT EXISTS idx_fact_status   ON fact_sales(order_status);
CREATE INDEX IF NOT EXISTS idx_dim_date_ym   ON dim_date(year_month);
CREATE INDEX IF NOT EXISTS idx_dim_date_year ON dim_date(year);
