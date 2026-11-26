-- Monthly OTIF and lead time with a 3-month moving average (window frame).
WITH monthly AS (
    SELECT
        d.month_key,
        MAX(d.is_festive)             AS festive_month,
        COUNT(*)                      AS order_items,
        AVG(1.0 * f.otif_flag)        AS otif_rate,
        AVG(1.0 * f.lead_time_days)   AS avg_lead_time_days
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.calendar_date = f.order_date
    WHERE f.delivery_count > 0
    GROUP BY d.month_key
)
SELECT
    monthly.*,
    AVG(otif_rate) OVER (
        ORDER BY month_key ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS otif_rate_3m_avg
FROM monthly
ORDER BY month_key
