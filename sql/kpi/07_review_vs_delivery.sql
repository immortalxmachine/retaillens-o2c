-- Does late delivery drive complaints? Review outcome of delivered orders by delivery outcome.
WITH orders AS (
    SELECT
        f.order_id,
        MAX(f.on_time_flag)                        AS on_time,
        MAX(f.review_score)                        AS review_score,
        MAX(f.low_review_flag)                     AS low_review
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    WHERE f.in_full_flag = 1 AND f.has_review = 1
    GROUP BY f.order_id
)
SELECT
    CASE WHEN on_time = 1 THEN 'on time' ELSE 'late' END AS delivery_outcome,
    COUNT(*)                                       AS orders,
    AVG(1.0 * low_review)                          AS low_review_rate,
    AVG(1.0 * review_score)                        AS avg_review_score,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER ()         AS share_of_orders
FROM orders
GROUP BY CASE WHEN on_time = 1 THEN 'on time' ELSE 'late' END
ORDER BY delivery_outcome
