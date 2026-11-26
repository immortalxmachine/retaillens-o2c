-- fact_order_item  (ZC_SalesOrderItem = "consumption view": what reports read)
-- Grain: one row per sales order item (VBAP). Header data from VBAK, delivery dates from
-- LIKP/LIPS, payment approval from BSAD and the review score from ZREVIEW.
-- OTIF and lead-time definitions live here once, so every KPI and dashboard agrees.
CREATE VIEW ZC_SalesOrderItem AS
WITH delivery AS (
    SELECT
        i.vgbel       AS order_id,       -- LIPS.VGBEL reference sales order
        i.vgpos       AS order_item,     -- LIPS.VGPOS reference order item
        h.wadat_ist   AS gi_ts,          -- LIKP.WADAT_IST goods issue = carrier hand-off
        h.podat       AS pod_ts,         -- LIKP.PODAT proof of delivery = customer received
        i.wadat       AS ship_limit_ts   -- LIPS.WADAT seller ship-by date
    FROM cln_lips AS i
    JOIN cln_likp AS h ON h.vbeln = i.vbeln
),
payment AS (
    SELECT vbeln AS order_id, MIN(augdt) AS approved_ts      -- BSAD.AUGDT payment approval
    FROM cln_bsad
    GROUP BY vbeln
),
review AS (
    SELECT vbeln AS order_id, MIN(score) AS review_score     -- worst score if several reviews
    FROM cln_zreview
    GROUP BY vbeln
)
SELECT
    i.vbeln                    AS order_id,
    i.posnr                    AS order_item,
    h.erdat                    AS order_ts,          -- VBAK.ERDAT purchase timestamp
    DATE_KEY(h.erdat)          AS order_date_key,
    h.vdatu                    AS promised_date,     -- VBAK.VDATU estimated delivery date
    h.kunnr                    AS customer_id,
    i.matnr                    AS material_id,
    i.zzlifnr                  AS seller_id,
    h.zzstatus                 AS order_status,
    i.kwmeng                   AS ordered_qty,
    i.netwr                    AS item_value,        -- VBAP.NETWR item price (BRL)
    i.zzfreight                AS freight_value,
    p.approved_ts,
    d.gi_ts,
    d.pod_ts,
    d.ship_limit_ts,
    CASE WHEN h.zzstatus = 'delivered' AND d.pod_ts IS NOT NULL
         THEN i.kwmeng ELSE 0 END AS delivered_qty,
    CASE WHEN h.zzstatus IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS cancelled_flag,
    -- OTIF population: orders with a final outcome (delivered with a date, or cancelled)
    CASE WHEN h.zzstatus IN ('canceled', 'unavailable')
           OR (h.zzstatus = 'delivered' AND d.pod_ts IS NOT NULL) THEN 1 ELSE 0 END
                               AS otif_eligible,
    HOURS_BETWEEN(h.erdat, p.approved_ts)  AS approval_hours,
    DAYS_BETWEEN(p.approved_ts, d.gi_ts)   AS approval_to_gi_days,
    DAYS_BETWEEN(d.gi_ts, d.pod_ts)        AS transit_days,
    DAYS_BETWEEN(h.erdat, d.pod_ts)        AS lead_time_days,
    DAYS_BETWEEN(h.erdat, h.vdatu)         AS promised_days,
    -- on time = received on or before the promised (estimated) date
    CASE WHEN d.pod_ts IS NOT NULL AND DAYS_BETWEEN(h.vdatu, d.pod_ts) <= 0
         THEN 1 ELSE 0 END AS on_time_flag,
    -- in full = the order was not cancelled and the item reached the customer
    CASE WHEN h.zzstatus = 'delivered' AND d.pod_ts IS NOT NULL THEN 1 ELSE 0 END AS in_full_flag,
    CASE WHEN h.zzstatus = 'delivered' AND d.pod_ts IS NOT NULL
          AND DAYS_BETWEEN(h.vdatu, d.pod_ts) <= 0 THEN 1 ELSE 0 END AS otif_flag,
    CASE WHEN d.gi_ts IS NULL OR d.ship_limit_ts IS NULL THEN NULL
         WHEN d.gi_ts <= d.ship_limit_ts THEN 1 ELSE 0 END AS seller_on_time_flag,
    r.review_score,
    CASE WHEN r.review_score IS NOT NULL THEN 1 ELSE 0 END AS has_review,
    CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END AS low_review_flag
FROM cln_vbap AS i
JOIN cln_vbak AS h ON h.vbeln = i.vbeln
LEFT JOIN delivery AS d ON d.order_id = i.vbeln AND d.order_item = i.posnr
LEFT JOIN payment AS p ON p.order_id = i.vbeln
LEFT JOIN review AS r ON r.order_id = i.vbeln;
