-- Fashion & accessories vs. the rest of the assortment (the case-study client's focus).
WITH items AS (
    SELECT f.*, m.segment
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    JOIN ZI_Material AS m ON m.material_id = f.material_id
    WHERE f.otif_eligible = 1
),
by_segment AS (
    SELECT
        segment,
        COUNT(*)                                                     AS order_items,
        SUM(CASE WHEN cancelled_flag = 0 THEN item_value ELSE 0 END) AS net_revenue,
        AVG(item_value)                                              AS avg_item_price,
        AVG(freight_value / NULLIF(item_value, 0))                   AS freight_to_price,
        AVG(1.0 * otif_flag)                                         AS otif_rate,
        AVG(1.0 * cancelled_flag)                                    AS cancellation_rate,
        AVG(CASE WHEN has_review = 1 THEN 1.0 * low_review_flag END) AS low_review_rate,
        AVG(CASE WHEN in_full_flag = 1 THEN 1.0 * lead_time_days END) AS avg_lead_time_days
    FROM items
    GROUP BY segment
)
SELECT
    by_segment.*,
    net_revenue / SUM(net_revenue) OVER () AS revenue_share
FROM by_segment
ORDER BY segment
