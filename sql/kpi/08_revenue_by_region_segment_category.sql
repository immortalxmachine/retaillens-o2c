-- Net revenue (non-cancelled item value) by state, macro-region, segment and category.
SELECT
    c.macro_region,
    c.state,
    m.segment,
    m.category,
    COUNT(*)            AS order_items,
    SUM(f.item_value)   AS net_revenue,
    SUM(f.freight_value) AS freight_revenue
FROM ZC_SalesOrderItem AS f
JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
JOIN ZI_Customer AS c ON c.customer_id = f.customer_id
JOIN ZI_Material AS m ON m.material_id = f.material_id
WHERE f.cancelled_flag = 0
GROUP BY c.macro_region, c.state, m.segment, m.category
ORDER BY net_revenue DESC
