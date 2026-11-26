-- fact_billing  (ZC_BillingItem)
-- Grain: one row per billing document item (VBRP) with header (VBRK), the payment that
-- cleared the invoice (BSAD) and any quantity returned against it (return orders).
CREATE VIEW ZC_BillingItem AS
WITH ret AS (
    SELECT vgbel AS billing_id, vgpos AS billing_item,
           SUM(kwmeng) AS returned_qty, SUM(netwr) AS returned_value
    FROM cln_returns
    GROUP BY vgbel, vgpos
),
pay AS (
    SELECT vbeln AS billing_id, MAX(augdt) AS clearing_date
    FROM cln_bsad
    GROUP BY vbeln
)
SELECT
    i.vbeln                   AS billing_id,
    i.posnr                   AS billing_item,
    h.fkdat                   AS billing_date,     -- VBRK.FKDAT billing date
    h.kunag                   AS customer_id,      -- VBRK.KUNAG sold-to party
    i.matnr                   AS material_id,
    i.aubel                   AS order_id,         -- VBRP.AUBEL sales order reference
    i.vgbel                   AS delivery_id,      -- VBRP.VGBEL delivery reference
    i.fkimg                   AS billed_qty,       -- VBRP.FKIMG billed quantity
    i.netwr                   AS net_revenue,      -- VBRP.NETWR net value (revenue)
    p.clearing_date,                               -- BSAD.AUGDT clearing (payment) date
    DAYS_BETWEEN(h.fkdat, p.clearing_date) AS days_to_cash,
    COALESCE(r.returned_qty, 0)   AS returned_qty,
    COALESCE(r.returned_value, 0) AS returned_value
FROM cln_vbrp AS i
JOIN cln_vbrk AS h ON h.vbeln = i.vbeln
LEFT JOIN pay AS p ON p.billing_id = i.vbeln
LEFT JOIN ret AS r
       ON r.billing_id = i.vbeln
      AND r.billing_item = i.posnr;
