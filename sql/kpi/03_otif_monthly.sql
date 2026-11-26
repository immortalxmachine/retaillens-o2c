-- Monthly OTIF and lead time with a 3-month moving average (window frame).
WITH monthly AS (
    SELECT
        d.month_key,
        MAX(d.is_festive)                          AS festive_month,
        COUNT(DISTINCT f.order_id)                 AS orders,
        AVG(1.0 * f.otif_flag)                     AS otif_rate,
        AVG(CASE WHEN f.in_full_flag = 1 THEN 1.0 * f.lead_time_days END) AS avg_lead_time_days
    FROM ZC_SalesOrderItem AS f
    JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
    WHERE f.otif_eligible = 1
    GROUP BY d.month_key
)
SELECT
    monthly.*,
    AVG(otif_rate) OVER (
        ORDER BY month_key ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS otif_rate_3m_avg
FROM monthly
ORDER BY month_key
