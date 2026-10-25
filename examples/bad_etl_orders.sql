-- ============================================================================
-- Sample Daily Executive Revenue Rollup (Contains 4 Expensive Anti-Patterns)
-- Target Engine: Databricks SQL / Apache Spark
-- ============================================================================

INSERT OVERWRITE TABLE gold.merchant_monthly_summary
SELECT
    e.*,
    o.*,
    m.merchant_name,
    m.category
FROM gold.fact_events e
INNER JOIN silver.orders o
    ON CAST(e.user_id AS STRING) = CAST(o.customer_id AS STRING)
LEFT JOIN dim.merchants m
    ON e.merchant_id = m.merchant_id
CROSS JOIN (
    SELECT DISTINCT currency_code FROM silver.orders
) fx
WHERE
    DATE_FORMAT(e.event_date, 'yyyy-MM') = '2026-10'
    AND YEAR(o.order_month) = 2026;
