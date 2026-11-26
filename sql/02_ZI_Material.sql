-- dim_material  (ZI_Material = MARA material master + MAKT English description)
CREATE VIEW ZI_Material AS
SELECT
    m.matnr AS material_id,    -- MARA.MATNR material number
    t.maktx AS material_name,  -- MAKT.MAKTX description
    m.matkl AS category,       -- MARA.MATKL material group (product category)
    m.saiso AS season          -- MARA.SAISO season: SS, AW or CORE
FROM cln_mara AS m
LEFT JOIN cln_makt AS t
       ON t.matnr = m.matnr
      AND t.spras = 'E';       -- language key: English
