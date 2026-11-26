-- fact_order_item  (ZC_SalesOrderItem = "consumption view": what reports read)
-- Grain: one row per sales order item (VBAP), enriched with header (VBAK) data and the
-- delivery outcome aggregated from LIPS/LIKP. OTIF flags are calculated here once,
-- so every KPI query and dashboard uses the same definition.
CREATE VIEW ZC_SalesOrderItem AS
WITH delivered AS (
    -- all deliveries for an order item (partial deliveries = more than one row in LIPS)
    SELECT
        i.vgbel               AS order_id,     -- LIPS.VGBEL reference sales order
        i.vgpos               AS order_item,   -- LIPS.VGPOS reference order item
        SUM(i.lfimg)          AS delivered_qty,
        MIN(h.wadat_ist)      AS first_gi_date,
        MAX(h.wadat_ist)      AS last_gi_date,
        COUNT(DISTINCT i.vbeln) AS delivery_count
    FROM cln_lips AS i
    JOIN cln_likp AS h ON h.vbeln = i.vbeln
    GROUP BY i.vgbel, i.vgpos
)
SELECT
    h.vbeln                   AS order_id,
    i.posnr                   AS order_item,
    h.erdat                   AS order_date,       -- VBAK.ERDAT created on
    h.vdatu                   AS requested_date,   -- VBAK.VDATU requested delivery date
    h.kunnr                   AS customer_id,
    i.matnr                   AS material_id,
    i.kwmeng                  AS ordered_qty,      -- VBAP.KWMENG order quantity
    i.netwr                   AS order_value,      -- VBAP.NETWR net value
    h.waerk                   AS currency,
    COALESCE(d.delivered_qty, 0)  AS delivered_qty,
    d.first_gi_date,
    d.last_gi_date,
    COALESCE(d.delivery_count, 0) AS delivery_count,
    -- order-to-delivery lead time: order creation -> last goods issue
    DAYS_BETWEEN(h.erdat, d.last_gi_date) AS lead_time_days,
    CASE WHEN d.last_gi_date <= h.vdatu THEN 1 ELSE 0 END AS on_time_flag,
    CASE WHEN COALESCE(d.delivered_qty, 0) >= i.kwmeng THEN 1 ELSE 0 END AS in_full_flag,
    -- OTIF = complete quantity shipped by the requested date
    CASE WHEN d.last_gi_date <= h.vdatu
          AND COALESCE(d.delivered_qty, 0) >= i.kwmeng THEN 1 ELSE 0 END AS otif_flag
FROM cln_vbap AS i
JOIN cln_vbak AS h ON h.vbeln = i.vbeln
LEFT JOIN delivered AS d
       ON d.order_id = i.vbeln
      AND d.order_item = i.posnr;
