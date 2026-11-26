-- Invoice-to-cash days (billing date -> clearing date), DSO-style, per country.
WITH invoices AS (
    SELECT
        b.billing_id,
        c.country,
        SUM(b.net_revenue)   AS invoice_value,
        MIN(b.days_to_cash)  AS days_to_cash,
        MIN(b.clearing_date) AS clearing_date
    FROM ZC_BillingItem AS b
    JOIN ZI_Customer AS c ON c.customer_id = b.customer_id
    GROUP BY b.billing_id, c.country
),
by_country AS (
    SELECT
        country,
        COUNT(*) AS invoices,
        AVG(CASE WHEN clearing_date IS NOT NULL THEN 1.0 * days_to_cash END)
            AS avg_invoice_to_cash_days,
        -- share of paid invoices that were paid more than 45 days after billing
        AVG(CASE WHEN clearing_date IS NOT NULL
                 THEN (CASE WHEN days_to_cash > 45 THEN 1.0 ELSE 0.0 END) END)
            AS share_paid_after_45d,
        SUM(CASE WHEN clearing_date IS NULL THEN invoice_value ELSE 0 END)
            AS open_receivables_value
    FROM invoices
    GROUP BY country
)
SELECT
    by_country.*,
    RANK() OVER (ORDER BY avg_invoice_to_cash_days DESC) AS slowest_rank   -- 1 = slowest payer
FROM by_country
ORDER BY slowest_rank
