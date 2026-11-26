-- Cash side of O2C: payment mix, instalments and time from purchase to payment approval.
-- Olist customers pay at checkout, so this replaces a classic invoice-to-cash / DSO metric.
WITH pay AS (
    SELECT p.*
    FROM ZC_Payment AS p
    JOIN ZI_CalendarDate AS d ON d.date_key = p.order_date_key AND d.in_analysis_window = 1
),
by_type AS (
    SELECT
        payment_type,
        COUNT(*)                                   AS payments,
        COUNT(DISTINCT order_id)                   AS orders,
        SUM(amount)                                AS amount,
        AVG(1.0 * installments)                    AS avg_installments,
        AVG(CASE WHEN installments > 1 THEN 1.0 ELSE 0.0 END) AS share_in_installments,
        AVG(approval_hours)                        AS avg_approval_hours,
        AVG(CASE WHEN approval_hours > 24 THEN 1.0 ELSE 0.0 END) AS share_approved_after_24h
    FROM pay
    GROUP BY payment_type
)
SELECT
    by_type.*,
    amount / SUM(amount) OVER ()                   AS amount_share,   -- share of all paid value
    RANK() OVER (ORDER BY amount DESC)             AS amount_rank
FROM by_type
ORDER BY amount_rank
