-- dim_customer  (CDS-style name: ZI_Customer = "interface view" on KNA1)
-- One row per real customer (Olist customer_unique_id) that passed data-quality checks.
CREATE VIEW ZI_Customer AS
SELECT
    kunnr AS customer_id,      -- KNA1.KUNNR customer number
    ort01 AS city,             -- KNA1.ORT01 city
    regio AS state,            -- KNA1.REGIO region = Brazilian state (SP, RJ, ...)
    land1 AS country,          -- KNA1.LAND1 country key (BR)
    pstlz AS zip_prefix,       -- KNA1.PSTLZ postal code (first 5 digits)
    -- IBGE macro-regions of Brazil, used to group the 27 states
    CASE
        WHEN regio IN ('AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO') THEN 'North'
        WHEN regio IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE') THEN 'Northeast'
        WHEN regio IN ('DF', 'GO', 'MT', 'MS') THEN 'Center-West'
        WHEN regio IN ('ES', 'MG', 'RJ', 'SP') THEN 'Southeast'
        WHEN regio IN ('PR', 'RS', 'SC') THEN 'South'
        ELSE 'Unknown'
    END AS macro_region
FROM cln_kna1;
