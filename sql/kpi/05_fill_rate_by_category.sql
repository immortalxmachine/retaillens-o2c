-- Fill rate (delivered qty / ordered qty) and share of split-delivered items by category.
SELECT
    m.category,
    SUM(f.ordered_qty)                                  AS ordered_qty,
    SUM(f.delivered_qty)                                AS delivered_qty,
    1.0 * SUM(f.delivered_qty) / SUM(f.ordered_qty)     AS fill_rate,
    AVG(CASE WHEN f.delivery_count > 1 THEN 1.0 ELSE 0.0 END) AS split_delivery_share
FROM ZC_SalesOrderItem AS f
JOIN ZI_Material AS m ON m.material_id = f.material_id
WHERE f.delivery_count > 0
GROUP BY m.category
ORDER BY fill_rate
