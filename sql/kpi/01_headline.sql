-- Headline O2C KPIs in one row (feeds metrics.json, README and the dashboard tiles).
-- Scope: orders placed inside the analysis window (complete months only).
WITH items AS (
    SELECT f.*, m.segment
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    JOIN ZI_Material AS m ON m.material_id = f.material_id
),
orders AS (
    -- order level: one review and one approval per order
    SELECT order_id,
           MAX(has_review) AS has_review, MAX(low_review_flag) AS low_review_flag,
           MAX(review_score) AS review_score, MAX(approval_hours) AS approval_hours
    FROM items
    GROUP BY order_id
)
SELECT
    (SELECT COUNT(DISTINCT order_id) FROM items)                           AS sales_orders,
    (SELECT COUNT(*) FROM items)                                           AS order_items,
    (SELECT COUNT(DISTINCT customer_id) FROM items)                        AS customers,
    (SELECT COUNT(DISTINCT seller_id) FROM items)                          AS sellers,
    -- revenue = item value of orders that were not cancelled
    (SELECT SUM(item_value) FROM items WHERE cancelled_flag = 0)           AS net_revenue,
    (SELECT SUM(freight_value) FROM items WHERE cancelled_flag = 0)        AS freight_revenue,
    (SELECT AVG(1.0 * otif_flag) FROM items WHERE otif_eligible = 1)       AS otif_rate,
    (SELECT AVG(1.0 * on_time_flag) FROM items
      WHERE otif_eligible = 1 AND in_full_flag = 1)                        AS on_time_rate,
    (SELECT AVG(1.0 * in_full_flag) FROM items WHERE otif_eligible = 1)    AS in_full_rate,
    (SELECT 1.0 * SUM(delivered_qty) / SUM(ordered_qty) FROM items
      WHERE otif_eligible = 1)                                             AS fill_rate,
    (SELECT AVG(1.0 * cancelled_flag) FROM items WHERE otif_eligible = 1)  AS cancellation_rate,
    (SELECT AVG(1.0 * lead_time_days) FROM items WHERE in_full_flag = 1)   AS avg_lead_time_days,
    (SELECT AVG(1.0 * promised_days) FROM items WHERE in_full_flag = 1)    AS avg_promised_days,
    (SELECT AVG(1.0 * transit_days) FROM items WHERE in_full_flag = 1)     AS avg_transit_days,
    (SELECT AVG(1.0 * seller_on_time_flag) FROM items
      WHERE seller_on_time_flag IS NOT NULL)                               AS seller_handover_on_time_rate,
    (SELECT AVG(approval_hours) FROM orders WHERE approval_hours IS NOT NULL) AS avg_approval_hours,
    (SELECT AVG(1.0 * low_review_flag) FROM orders WHERE has_review = 1)   AS low_review_rate,
    (SELECT AVG(1.0 * review_score) FROM orders WHERE has_review = 1)      AS avg_review_score,
    (SELECT 1.0 * SUM(CASE WHEN segment = 'Fashion & accessories' THEN item_value ELSE 0 END)
            / SUM(item_value) FROM items WHERE cancelled_flag = 0)         AS fashion_revenue_share
