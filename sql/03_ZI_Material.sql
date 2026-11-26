-- dim_material  (ZI_Material = MARA material master + T023T material-group texts)
-- Olist is multi-category. The case-study client serves fashion retail, so a "segment"
-- groups the apparel / shoes / bags / watches categories for a fashion drill-down.
CREATE VIEW ZI_Material AS
SELECT
    m.matnr AS material_id,                               -- MARA.MATNR
    m.matkl AS category_code,                             -- MARA.MATKL (Portuguese code)
    COALESCE(t.wgbez, m.matkl, 'uncategorized') AS category,  -- T023T.WGBEZ English text
    CASE
        WHEN COALESCE(t.wgbez, m.matkl) IN (
            'fashio_female_clothing', 'fashion_male_clothing', 'fashion_childrens_clothes',
            'fashion_underwear_beach', 'fashion_sport', 'fashion_shoes',
            'fashion_bags_accessories', 'luggage_accessories', 'watches_gifts'
        ) THEN 'Fashion & accessories'
        ELSE 'Other'
    END AS segment,
    m.brgew AS weight_g,                                  -- MARA.BRGEW gross weight (g)
    m.laeng * m.breit * m.hoehe AS volume_cm3             -- MARA.LAENG/BREIT/HOEHE (cm)
FROM cln_mara AS m
LEFT JOIN cln_t023t AS t
       ON t.matkl = m.matkl
      AND t.spras = 'E';      -- language key: English
