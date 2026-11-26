-- Headline O2C KPIs in one row (feeds metrics.json, README and the dashboard tiles).
-- OTIF / lead time use order items with at least one goods issue (items with no delivery at
-- all only exist because their delivery was quarantined by the DQ stage).
WITH shipped AS (
    SELECT * FROM ZC_SalesOrderItem WHERE delivery_count > 0
),
invoices AS (
    -- invoice level (not item level) for invoice-to-cash, like a DSO calculation
    SELECT billing_id, MIN(days_to_cash) AS days_to_cash, MIN(clearing_date) AS clearing_date,
           SUM(net_revenue) AS invoice_value
    FROM ZC_BillingItem
    GROUP BY billing_id
)
SELECT
    (SELECT SUM(net_revenue) FROM ZC_BillingItem)                     AS total_revenue,
    (SELECT COUNT(DISTINCT order_id) FROM ZC_SalesOrderItem)          AS sales_orders,
    (SELECT COUNT(*) FROM ZC_SalesOrderItem)                          AS order_items,
    (SELECT AVG(1.0 * otif_flag) FROM shipped)                        AS otif_rate,
    (SELECT AVG(1.0 * on_time_flag) FROM shipped)                     AS on_time_rate,
    (SELECT AVG(1.0 * in_full_flag) FROM shipped)                     AS in_full_rate,
    (SELECT AVG(1.0 * lead_time_days) FROM shipped)                   AS avg_lead_time_days,
    (SELECT 1.0 * SUM(delivered_qty) / SUM(ordered_qty) FROM shipped) AS fill_rate,
    (SELECT 1.0 * SUM(returned_qty) / SUM(billed_qty) FROM ZC_BillingItem) AS return_rate,
    (SELECT AVG(1.0 * days_to_cash) FROM invoices
      WHERE clearing_date IS NOT NULL)                                AS avg_invoice_to_cash_days,
    (SELECT 1.0 * SUM(CASE WHEN clearing_date IS NULL THEN invoice_value ELSE 0 END)
            / SUM(invoice_value) FROM invoices)                       AS open_receivables_share
