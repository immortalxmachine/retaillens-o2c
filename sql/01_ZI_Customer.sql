-- dim_customer  (CDS-style name: ZI_Customer = "interface view" on KNA1)
-- One row per sold-to customer that passed data-quality checks.
CREATE VIEW ZI_Customer AS
SELECT
    kunnr AS customer_id,      -- KNA1.KUNNR customer number
    name1 AS customer_name,    -- KNA1.NAME1 name
    land1 AS country,          -- KNA1.LAND1 country key
    regio AS region            -- KNA1.REGIO region within the country
FROM cln_kna1;
