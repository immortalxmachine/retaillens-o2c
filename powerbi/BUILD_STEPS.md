# Build the Power BI report - step by step (case study, real Olist data)

Run the pipeline on the full dataset first (`python -m src.pipeline`). It downloads Olist from
Kaggle if needed and exports the star schema to `powerbi/data/` as CSV and Parquet. The export is
about 50 MB, so it is not committed. You need Power BI Desktop (free, Windows) to build the
`.pbix`.

## 1. Import the data
1. Open Power BI Desktop > **Get data > Parquet** (or **Text/CSV**).
2. Load the seven files from `powerbi/data/`: `dim_customer`, `dim_seller`, `dim_material`,
   `dim_date`, `fact_order_item`, `fact_delivery`, `fact_payment`.
3. In Power Query, check the column types: `*_ts` and `promised_date` as **Date/Time**,
   `calendar_date` as **Date**, and `*_id` and `date_key` columns as **Text**. Then Close & Apply.

## 2. Model (Model view) - a star schema
Create single-direction, many-to-one relationships:

| From (many) | To (one) |
|---|---|
| fact_order_item[customer_id] | dim_customer[customer_id] |
| fact_order_item[material_id] | dim_material[material_id] |
| fact_order_item[seller_id] | dim_seller[seller_id] |
| fact_order_item[order_date_key] | dim_date[date_key] |
| fact_delivery[seller_id] | dim_seller[seller_id] |
| fact_delivery[material_id] | dim_material[material_id] |
| fact_delivery[gi_date_key] | dim_date[date_key] (inactive is fine) |
| fact_payment[customer_id] | dim_customer[customer_id] |
| fact_payment[order_date_key] | dim_date[date_key] (inactive if ambiguous) |

Then select `dim_date` > **Table tools > Mark as date table** > `calendar_date`.
Add a report-level filter `dim_date[in_analysis_window] = 1`.

## 3. Measures
Create the measures in `DAX_measures.md`: Total Revenue, OTIF %, Avg Lead Time (days),
Cancellation Rate %, Complaint Rate %, Avg Approval Hours, YoY Revenue %.

## 4. Report page "O2C Overview - Olist case study"
1. Title: **RetailLens - Order-to-Cash Overview (case study, Olist data CC BY-NC-SA 4.0)**.
2. Cards: Total Revenue, OTIF %, Avg Lead Time (days), Complaint Rate %, Avg Approval Hours.
3. Line chart: dim_date[month_key] on the X axis, Total Revenue on the Y axis.
4. Bar chart: dim_customer[state] by OTIF %, sorted ascending (worst first).
5. Bar chart: dim_material[category] by Complaint Rate %, top 10.
6. Slicers: dim_material[segment], dim_customer[macro_region], dim_date[year_num].

Check: the cards should match `metrics.json > headline`.

## 5. Save and screenshot
1. Save as `powerbi/RetailLens_O2C.pbix`.
2. Take a screenshot of the report page and save it as **`docs/screenshots/04-powerbi.png`**
   (keep it under 1 MB, for example a 1600 px wide PNG).
3. Commit both files (`docs: add Power BI report and screenshot`).
