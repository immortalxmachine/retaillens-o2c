-- Top 10 materials by revenue within each segment (RANK partitioned by segment) + overall rank.
WITH material_revenue AS (
    SELECT
        m.segment,
        m.category,
        m.material_id,
        COUNT(*)           AS items_sold,
        SUM(f.item_value)  AS net_revenue
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    JOIN ZI_Material AS m ON m.material_id = f.material_id
    WHERE f.cancelled_flag = 0
    GROUP BY m.segment, m.category, m.material_id
),
ranked AS (
    SELECT
        material_revenue.*,
        RANK() OVER (PARTITION BY segment ORDER BY net_revenue DESC) AS rank_in_segment,
        RANK() OVER (ORDER BY net_revenue DESC)                      AS overall_rank
    FROM material_revenue
)
SELECT *
FROM ranked
WHERE rank_in_segment <= 10
ORDER BY segment, rank_in_segment
