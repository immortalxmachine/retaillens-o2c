-- dim_seller  (ZI_Seller on LFA1 - Olist marketplace sellers as vendor master)
CREATE VIEW ZI_Seller AS
SELECT
    lifnr AS seller_id,        -- LFA1.LIFNR vendor number
    ort01 AS city,
    regio AS state,
    pstlz AS zip_prefix
FROM cln_lfa1;
