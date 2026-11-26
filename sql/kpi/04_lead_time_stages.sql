-- Where does the lead time go? Order-to-delivery split into its O2C stages per macro-region:
--   purchase -> payment approval -> carrier hand-off (goods issue) -> received by customer
SELECT
    c.macro_region,
    COUNT(*)                                       AS delivered_items,
    AVG(f.approval_hours) / 24.0                   AS avg_approval_days,
    AVG(1.0 * f.approval_to_gi_days)               AS avg_approval_to_gi_days,
    AVG(1.0 * f.transit_days)                      AS avg_transit_days,
    AVG(1.0 * f.lead_time_days)                    AS avg_lead_time_days,
    AVG(1.0 * f.promised_days)                     AS avg_promised_days,
    AVG(1.0 * f.on_time_flag)                      AS on_time_rate,
    -- share of the total lead time spent with the carrier
    AVG(1.0 * f.transit_days) / AVG(1.0 * f.lead_time_days) AS transit_share
FROM ZC_SalesOrderItem AS f
JOIN ZI_CalendarDate AS d ON d.date_key = f.order_date_key AND d.in_analysis_window = 1
JOIN ZI_Customer AS c ON c.customer_id = f.customer_id
WHERE f.in_full_flag = 1
GROUP BY c.macro_region
ORDER BY avg_lead_time_days DESC
