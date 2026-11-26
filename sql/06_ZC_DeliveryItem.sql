-- fact_delivery  (ZC_DeliveryItem)
-- Grain: one row per outbound delivery item (LIPS) with its header (LIKP).
-- Separates the two halves of logistics: seller hand-off vs. carrier transit.
CREATE VIEW ZC_DeliveryItem AS
SELECT
    i.vbeln                   AS delivery_id,
    i.posnr                   AS delivery_item,
    i.vgbel                   AS order_id,
    i.vgpos                   AS order_item,
    h.kunnr                   AS customer_id,
    i.zzlifnr                 AS seller_id,
    i.matnr                   AS material_id,
    i.lfimg                   AS delivered_qty,      -- LIPS.LFIMG
    i.wadat                   AS ship_limit_ts,      -- seller ship-by date
    h.wadat_ist               AS gi_ts,              -- carrier hand-off
    h.podat                   AS pod_ts,             -- received by customer
    h.lfdat                   AS promised_date,      -- LIKP.LFDAT planned delivery date
    DATE_KEY(h.wadat_ist)     AS gi_date_key,
    DAYS_BETWEEN(i.wadat, h.wadat_ist)  AS handover_delay_days,
    DAYS_BETWEEN(h.wadat_ist, h.podat)  AS transit_days,
    DAYS_BETWEEN(h.lfdat, h.podat)      AS days_vs_promise,   -- > 0 means late
    CASE WHEN h.wadat_ist > i.wadat THEN 1 ELSE 0 END AS handover_late_flag
FROM cln_lips AS i
JOIN cln_likp AS h ON h.vbeln = i.vbeln;
