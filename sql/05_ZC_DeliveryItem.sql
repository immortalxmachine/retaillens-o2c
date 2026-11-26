-- fact_delivery  (ZC_DeliveryItem)
-- Grain: one row per outbound delivery item (LIPS) with its header (LIKP).
CREATE VIEW ZC_DeliveryItem AS
SELECT
    i.vbeln                   AS delivery_id,
    i.posnr                   AS delivery_item,
    i.vgbel                   AS order_id,
    i.vgpos                   AS order_item,
    h.kunnr                   AS customer_id,
    i.matnr                   AS material_id,
    h.lfdat                   AS planned_date,     -- LIKP.LFDAT planned delivery date
    h.wadat_ist               AS goods_issue_date, -- LIKP.WADAT_IST actual goods issue
    i.lfimg                   AS delivered_qty,    -- LIPS.LFIMG delivered quantity
    DAYS_BETWEEN(h.lfdat, h.wadat_ist) AS days_late,
    CASE WHEN h.wadat_ist > h.lfdat THEN 1 ELSE 0 END AS late_flag
FROM cln_lips AS i
JOIN cln_likp AS h ON h.vbeln = i.vbeln;
