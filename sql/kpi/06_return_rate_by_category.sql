-- Return rate (returned qty / billed qty) by category, ranked highest first.
WITH by_category AS (
    SELECT
        m.category,
        SUM(b.billed_qty)       AS billed_qty,
        SUM(b.returned_qty)     AS returned_qty,
        SUM(b.net_revenue)      AS net_revenue,
        SUM(b.returned_value)   AS returned_value
    FROM ZC_BillingItem AS b
    JOIN ZI_Material AS m ON m.material_id = b.material_id
    GROUP BY m.category
)
SELECT
    category,
    billed_qty,
    returned_qty,
    1.0 * returned_qty / billed_qty AS return_rate,
    net_revenue,
    returned_value,
    RANK() OVER (ORDER BY 1.0 * returned_qty / billed_qty DESC) AS return_rank
FROM by_category
ORDER BY return_rank
