# Build the Power BI report - step by step (SYNTHETIC DATA)

The pipeline (`python -m src.pipeline`) exports the star schema to `powerbi/data/` as CSV and
Parquet. The Parquet files are committed; the larger CSV copies are created when you run the
pipeline. Power BI Desktop (free, Windows) is needed to build the `.pbix`.

## 1. Import the data
1. Open Power BI Desktop > **Get data > Parquet** (or **Text/CSV**).
2. Load the six files from `powerbi/data/`: `dim_customer`, `dim_material`, `dim_date`,
   `fact_order_item`, `fact_delivery`, `fact_billing`.
3. In Power Query make sure the date columns are type **Date** and `*_id` columns are **Text**
   (IDs like `0000100001` must keep their leading zeros). Close & Apply.

## 2. Model (Model view) - a star schema
Create single-direction, many-to-one relationships:

| From (many) | To (one) |
|---|---|
| fact_order_item[customer_id] | dim_customer[customer_id] |
| fact_order_item[material_id] | dim_material[material_id] |
| fact_order_item[order_date] | dim_date[calendar_date] |
| fact_billing[customer_id] | dim_customer[customer_id] |
| fact_billing[material_id] | dim_material[material_id] |
| fact_billing[billing_date] | dim_date[calendar_date] |
| fact_delivery[customer_id] | dim_customer[customer_id] |
| fact_delivery[material_id] | dim_material[material_id] |
| fact_delivery[goods_issue_date] | dim_date[calendar_date] (inactive is fine) |

Then select `dim_date` > **Table tools > Mark as date table** > `calendar_date`.

## 3. Measures
Create the measures in `DAX_measures.md` (Total Revenue, OTIF %, Avg Lead Time, Return Rate %,
YoY Revenue %). Format: percentages as %, revenue as currency EUR.

## 4. Report page "O2C Overview - SYNTHETIC DATA"
1. Title text box: **RetailLens - Order-to-Cash Overview (SYNTHETIC DATA)**.
2. Cards: Total Revenue, OTIF %, Avg Lead Time (days), Return Rate %, YoY Revenue %.
3. Line chart: dim_date[month_key] on X, Total Revenue on Y.
4. Bar chart: dim_customer[country] by OTIF % (sort ascending - worst first).
5. Bar chart: dim_material[category] by Return Rate % (sort descending).
6. Slicers: dim_material[season], dim_customer[country], dim_date[year_num].

Check: the cards should match `metrics.json > headline` (same definitions as the SQL).

## 5. Save and screenshot
1. Save as `powerbi/RetailLens_O2C.pbix`.
2. Take a screenshot of the report page and save it as **`docs/screenshots/04-powerbi.png`**
   (keep it under 1 MB, e.g. 1600 px wide PNG).
3. Commit both files (`docs: add Power BI report and screenshot`).
