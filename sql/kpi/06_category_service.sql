-- Service quality by category. Olist has NO returns table, so two honest proxies are used:
--   cancellation_rate  = items in cancelled / unavailable orders
--   low_review_rate    = items whose order got a review score of 1 or 2 (complaint)
-- Only categories with at least 500 eligible items are ranked.
WITH items AS (
    SELECT f.*, m.category, m.segment
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    JOIN ZI_Material AS m ON m.material_id = f.material_id
    WHERE f.otif_eligible = 1
),
by_category AS (
    SELECT
        category,
        segment,
        COUNT(*)                                                   AS order_items,
        SUM(CASE WHEN cancelled_flag = 0 THEN item_value ELSE 0 END) AS net_revenue,
        AVG(1.0 * cancelled_flag)                                  AS cancellation_rate,
        AVG(CASE WHEN has_review = 1 THEN 1.0 * low_review_flag END) AS low_review_rate,
        AVG(CASE WHEN has_review = 1 THEN 1.0 * review_score END)  AS avg_review_score,
        AVG(1.0 * otif_flag)                                       AS otif_rate,
        AVG(freight_value / NULLIF(item_value, 0))                 AS freight_to_price
    FROM items
    GROUP BY category, segment
)
SELECT
    by_category.*,
    CASE WHEN order_items >= 500
         THEN RANK() OVER (PARTITION BY CASE WHEN order_items >= 500 THEN 1 ELSE 0 END
                           ORDER BY low_review_rate DESC)
    END AS complaint_rank                            -- 1 = most complaints (min. 500 items)
FROM by_category
ORDER BY complaint_rank NULLS LAST, order_items DESC   -- unranked (small) categories last
