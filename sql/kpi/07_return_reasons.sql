-- Return reasons (AUGRU) per category, with the share of each reason inside its category.
WITH reasons AS (
    SELECT
        m.category,
        r.augru               AS reason_code,
        SUM(r.kwmeng)         AS returned_qty
    FROM cln_returns AS r
    JOIN ZI_Material AS m ON m.material_id = r.matnr
    GROUP BY m.category, r.augru
)
SELECT
    category,
    reason_code,
    CASE reason_code
        WHEN 'R01' THEN 'Size / fit'
        WHEN 'R02' THEN 'Quality defect'
        WHEN 'R03' THEN 'Not as described'
        WHEN 'R04' THEN 'Delivered too late'
    END AS reason_text,
    returned_qty,
    1.0 * returned_qty / SUM(returned_qty) OVER (PARTITION BY category) AS share_in_category
FROM reasons
ORDER BY category, returned_qty DESC
