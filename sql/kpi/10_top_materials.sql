-- Top 3 materials per category by revenue (RANK partitioned by category) + overall rank.
WITH material_revenue AS (
    SELECT
        m.category,
        m.material_id,
        m.material_name,
        SUM(b.net_revenue) AS net_revenue,
        SUM(b.billed_qty)  AS billed_qty
    FROM ZC_BillingItem AS b
    JOIN ZI_Material AS m ON m.material_id = b.material_id
    GROUP BY m.category, m.material_id, m.material_name
),
ranked AS (
    SELECT
        material_revenue.*,
        RANK() OVER (PARTITION BY category ORDER BY net_revenue DESC) AS rank_in_category,
        RANK() OVER (ORDER BY net_revenue DESC)                       AS overall_rank
    FROM material_revenue
)
SELECT *
FROM ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category
