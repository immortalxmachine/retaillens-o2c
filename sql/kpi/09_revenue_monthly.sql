-- Monthly revenue with month-over-month and year-over-year growth (LAG window function).
WITH monthly AS (
    SELECT
        d.month_key,
        MAX(d.is_festive)  AS festive_month,
        SUM(b.net_revenue) AS net_revenue
    FROM ZC_BillingItem AS b
    JOIN ZI_CalendarDate AS d ON d.calendar_date = b.billing_date
    GROUP BY d.month_key
)
SELECT
    month_key,
    festive_month,
    net_revenue,
    LAG(net_revenue, 1) OVER (ORDER BY month_key)                     AS prev_month_revenue,
    net_revenue / LAG(net_revenue, 1) OVER (ORDER BY month_key) - 1   AS mom_growth,
    LAG(net_revenue, 12) OVER (ORDER BY month_key)                    AS same_month_last_year,
    net_revenue / LAG(net_revenue, 12) OVER (ORDER BY month_key) - 1  AS yoy_growth
FROM monthly
ORDER BY month_key
