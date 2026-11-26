-- OTIF, lead time and transit time per customer state, ranked worst-first.
-- States with fewer than 300 eligible items are kept but not ranked (too small to judge).
WITH items AS (
    SELECT f.*, c.state, c.macro_region
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    JOIN ZI_Customer AS c ON c.customer_id = f.customer_id
    WHERE f.otif_eligible = 1
),
by_state AS (
    SELECT
        state,
        macro_region,
        COUNT(*)                                   AS order_items,
        AVG(1.0 * otif_flag)                       AS otif_rate,
        AVG(CASE WHEN in_full_flag = 1 THEN 1.0 * on_time_flag END)   AS on_time_rate,
        AVG(CASE WHEN in_full_flag = 1 THEN 1.0 * lead_time_days END) AS avg_lead_time_days,
        AVG(CASE WHEN in_full_flag = 1 THEN 1.0 * transit_days END)   AS avg_transit_days,
        AVG(CASE WHEN in_full_flag = 1 THEN 1.0 * promised_days END)  AS avg_promised_days
    FROM items
    GROUP BY state, macro_region
)
SELECT
    by_state.*,
    CASE WHEN order_items >= 300
         THEN RANK() OVER (PARTITION BY CASE WHEN order_items >= 300 THEN 1 ELSE 0 END
                           ORDER BY otif_rate ASC)
    END AS worst_otif_rank                           -- 1 = worst state with enough volume
FROM by_state
ORDER BY otif_rate ASC
