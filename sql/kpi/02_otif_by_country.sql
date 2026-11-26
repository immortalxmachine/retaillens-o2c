-- OTIF, on-time, in-full and lead time per customer country, ranked worst-first.
WITH item_country AS (
    SELECT f.*, c.country
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_Customer AS c ON c.customer_id = f.customer_id
    WHERE f.delivery_count > 0
),
by_country AS (
    SELECT
        country,
        COUNT(*)                      AS order_items,
        AVG(1.0 * otif_flag)          AS otif_rate,
        AVG(1.0 * on_time_flag)       AS on_time_rate,
        AVG(1.0 * in_full_flag)       AS in_full_rate,
        AVG(1.0 * lead_time_days)     AS avg_lead_time_days
    FROM item_country
    GROUP BY country
)
SELECT
    by_country.*,
    RANK() OVER (ORDER BY otif_rate ASC) AS worst_otif_rank   -- 1 = worst country
FROM by_country
ORDER BY worst_otif_rank
