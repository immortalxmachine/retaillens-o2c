-- fact_payment  (ZC_Payment)
-- Grain: one row per payment line (BSAD). Olist customers pay at checkout, so the
-- cash side of O2C is "purchase -> payment approved", not "invoice -> cash after 30 days".
CREATE VIEW ZC_Payment AS
SELECT
    p.belnr                   AS payment_id,
    p.vbeln                   AS order_id,
    p.kunnr                   AS customer_id,
    p.zlsch                   AS payment_type,       -- credit_card, boleto, voucher, debit_card
    p.zzinstallments          AS installments,
    p.dmbtr                   AS amount,             -- BSAD.DMBTR (BRL)
    h.erdat                   AS order_ts,
    DATE_KEY(h.erdat)         AS order_date_key,
    p.augdt                   AS approved_ts,        -- BSAD.AUGDT clearing = approval
    HOURS_BETWEEN(h.erdat, p.augdt) AS approval_hours
FROM cln_bsad AS p
JOIN cln_vbak AS h ON h.vbeln = p.vbeln;
