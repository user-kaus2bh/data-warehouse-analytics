-- ============================================================
-- analytics/kpi_queries.sql
-- Business KPI Views built on top of the star schema
--
-- Views created:
--   vw_monthly_revenue        → revenue trend by month/year
--   vw_revenue_by_region      → sales performance by geography
--   vw_revenue_by_segment     → sales by customer segment
--   vw_top_products           → product performance ranking
--   vw_category_performance   → category-level P&L
--   vw_campaign_roi           → marketing campaign effectiveness
--   vw_customer_ltv           → customer lifetime value
--   vw_cohort_monthly         → monthly customer cohort revenue
--   vw_channel_performance    → sales channel analysis
--   vw_yoy_comparison         → year-over-year revenue comparison
-- ============================================================


-- ─── 1. Monthly Revenue Trend ─────────────────────────────────────────────────
DROP VIEW IF EXISTS vw_monthly_revenue;
CREATE VIEW vw_monthly_revenue AS
SELECT
    d.year,
    d.month,
    d.month_name,
    d.year_month,
    d.quarter,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    COUNT(*)                   AS total_line_items,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    COUNT(DISTINCT f.customer_key)      AS unique_customers,
    ROUND(SUM(f.line_revenue) /
          NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.is_revenue = 1
GROUP BY d.year, d.month, d.month_name, d.year_month, d.quarter
ORDER BY d.year, d.month;


-- ─── 2. Revenue by Region ─────────────────────────────────────────────────────
DROP VIEW IF EXISTS vw_revenue_by_region;
CREATE VIEW vw_revenue_by_region AS
SELECT
    c.region,
    d.year,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    COUNT(DISTINCT f.customer_key)      AS unique_customers,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    ROUND(SUM(f.line_revenue) /
          NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.rowid
JOIN dim_date     d ON f.date_key     = d.date_key
WHERE f.is_revenue = 1
GROUP BY c.region, d.year
ORDER BY d.year, total_revenue DESC;


-- ─── 3. Revenue by Customer Segment ──────────────────────────────────────────
DROP VIEW IF EXISTS vw_revenue_by_segment;
CREATE VIEW vw_revenue_by_segment AS
SELECT
    c.segment,
    d.year,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    COUNT(DISTINCT f.customer_key)      AS unique_customers,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    ROUND(SUM(f.line_revenue) /
          NULLIF(COUNT(DISTINCT f.customer_key), 0), 2) AS revenue_per_customer
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.rowid
JOIN dim_date     d ON f.date_key     = d.date_key
WHERE f.is_revenue = 1
GROUP BY c.segment, d.year
ORDER BY d.year, total_revenue DESC;


-- ─── 4. Top Products by Revenue ──────────────────────────────────────────────
DROP VIEW IF EXISTS vw_top_products;
CREATE VIEW vw_top_products AS
SELECT
    p.product_id,
    p.name              AS product_name,
    p.category,
    p.price_band,
    SUM(f.quantity)                     AS total_units_sold,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    COUNT(DISTINCT f.order_id)          AS times_ordered,
    COUNT(DISTINCT f.customer_key)      AS unique_buyers
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.rowid
WHERE f.is_revenue = 1
GROUP BY p.product_id, p.name, p.category, p.price_band
ORDER BY total_revenue DESC;


-- ─── 5. Category Performance ─────────────────────────────────────────────────
DROP VIEW IF EXISTS vw_category_performance;
CREATE VIEW vw_category_performance AS
SELECT
    p.category,
    d.year,
    COUNT(DISTINCT p.product_id)        AS num_products,
    SUM(f.quantity)                     AS total_units_sold,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_cost)                    AS total_cost,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    COUNT(DISTINCT f.order_id)          AS total_orders
FROM fact_sales f
JOIN dim_product p ON f.product_key = p.rowid
JOIN dim_date    d ON f.date_key    = d.date_key
WHERE f.is_revenue = 1
GROUP BY p.category, d.year
ORDER BY d.year, total_revenue DESC;


-- ─── 6. Campaign ROI ──────────────────────────────────────────────────────────
DROP VIEW IF EXISTS vw_campaign_roi;
CREATE VIEW vw_campaign_roi AS
SELECT
    ca.campaign_id,
    ca.name             AS campaign_name,
    ca.type             AS campaign_type,
    ca.goal,
    ca.budget,
    ca.status,
    COUNT(DISTINCT f.order_id)          AS attributed_orders,
    COUNT(DISTINCT f.customer_key)      AS attributed_customers,
    SUM(f.line_revenue)                 AS attributed_revenue,
    SUM(f.line_profit)                  AS attributed_profit,
    ROUND(ca.budget, 2)                 AS campaign_budget,
    ROUND(
        (SUM(f.line_revenue) - ca.budget) /
        NULLIF(ca.budget, 0) * 100, 1
    )                                   AS roi_pct
FROM fact_sales f
JOIN dim_campaign ca ON f.campaign_key = ca.rowid
WHERE f.is_revenue = 1
  AND f.campaign_key IS NOT NULL
GROUP BY ca.campaign_id, ca.name, ca.type, ca.goal, ca.budget, ca.status
ORDER BY attributed_revenue DESC;


-- ─── 7. Customer Lifetime Value (LTV) ────────────────────────────────────────
DROP VIEW IF EXISTS vw_customer_ltv;
CREATE VIEW vw_customer_ltv AS
SELECT
    c.customer_id,
    c.name,
    c.region,
    c.segment,
    c.joined_date,
    c.tenure_days,
    c.loyalty_score,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(SUM(f.line_revenue) /
          NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value,
    MIN(d.full_date)                    AS first_order_date,
    MAX(d.full_date)                    AS last_order_date,
    CASE
        WHEN SUM(f.line_revenue) > 500000 THEN 'Platinum'
        WHEN SUM(f.line_revenue) > 200000 THEN 'Gold'
        WHEN SUM(f.line_revenue) > 50000  THEN 'Silver'
        ELSE 'Bronze'
    END                                 AS ltv_tier
FROM fact_sales f
JOIN dim_customer c ON f.customer_key = c.rowid
JOIN dim_date     d ON f.date_key     = d.date_key
WHERE f.is_revenue = 1
GROUP BY c.customer_id, c.name, c.region, c.segment,
         c.joined_date, c.tenure_days, c.loyalty_score
ORDER BY total_revenue DESC;


-- ─── 8. Monthly Customer Cohort Revenue ──────────────────────────────────────
-- Groups customers by the month they first purchased, tracks their spend over time
DROP VIEW IF EXISTS vw_cohort_monthly;
CREATE VIEW vw_cohort_monthly AS
WITH first_purchase AS (
    SELECT
        f.customer_key,
        MIN(d.year_month) AS cohort_month
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE f.is_revenue = 1
    GROUP BY f.customer_key
)
SELECT
    fp.cohort_month,
    d.year_month        AS activity_month,
    COUNT(DISTINCT f.customer_key)  AS active_customers,
    SUM(f.line_revenue)             AS cohort_revenue,
    SUM(f.line_profit)              AS cohort_profit
FROM fact_sales f
JOIN dim_date   d  ON f.date_key     = d.date_key
JOIN first_purchase fp ON f.customer_key = fp.customer_key
WHERE f.is_revenue = 1
GROUP BY fp.cohort_month, d.year_month
ORDER BY fp.cohort_month, d.year_month;


-- ─── 9. Sales Channel Performance ────────────────────────────────────────────
DROP VIEW IF EXISTS vw_channel_performance;
CREATE VIEW vw_channel_performance AS
SELECT
    f.channel,
    d.year,
    COUNT(DISTINCT f.order_id)          AS total_orders,
    COUNT(DISTINCT f.customer_key)      AS unique_customers,
    SUM(f.line_revenue)                 AS total_revenue,
    SUM(f.line_profit)                  AS total_profit,
    ROUND(AVG(f.line_margin_pct), 1)    AS avg_margin_pct,
    ROUND(SUM(f.line_revenue) /
          NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_order_value
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.is_revenue = 1
GROUP BY f.channel, d.year
ORDER BY d.year, total_revenue DESC;


-- ─── 10. Year-over-Year Revenue Comparison ───────────────────────────────────
DROP VIEW IF EXISTS vw_yoy_comparison;
CREATE VIEW vw_yoy_comparison AS
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
        SUM(f.line_revenue) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    WHERE f.is_revenue = 1
    GROUP BY d.year, d.month, d.month_name
)
SELECT
    a.month,
    a.month_name,
    a.revenue                                       AS revenue_2022,
    b.revenue                                       AS revenue_2023,
    c.revenue                                       AS revenue_2024,
    ROUND((b.revenue - a.revenue) /
          NULLIF(a.revenue, 0) * 100, 1)            AS growth_22_23_pct,
    ROUND((c.revenue - b.revenue) /
          NULLIF(b.revenue, 0) * 100, 1)            AS growth_23_24_pct
FROM       monthly a
LEFT JOIN  monthly b ON a.month = b.month AND b.year = 2023
LEFT JOIN  monthly c ON a.month = c.month AND c.year = 2024
WHERE a.year = 2022
ORDER BY a.month;
