-- Net revenue sliced by country, region, season and category (the dashboard pivots this).
SELECT
    c.country,
    c.region,
    m.season,
    m.category,
    SUM(b.net_revenue) AS net_revenue,
    SUM(b.billed_qty)  AS billed_qty
FROM ZC_BillingItem AS b
JOIN ZI_Customer AS c ON c.customer_id = b.customer_id
JOIN ZI_Material AS m ON m.material_id = b.material_id
GROUP BY c.country, c.region, m.season, m.category
ORDER BY net_revenue DESC
