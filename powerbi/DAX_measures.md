# DAX measures - RetailLens (SYNTHETIC DATA)

Create these in Power BI Desktop (Modeling > New measure). They mirror the SQL definitions in
`sql/kpi/01_headline.sql`, so the Power BI numbers should match `metrics.json`.

Tables come from `powerbi/data/` (see `BUILD_STEPS.md`): `fact_order_item`, `fact_delivery`,
`fact_billing`, `dim_customer`, `dim_material`, `dim_date`.

```DAX
-- Revenue = sum of billed net value (VBRP.NETWR)
Total Revenue =
SUM ( fact_billing[net_revenue] )

-- Only items that were shipped at least once (same filter as the SQL)
Shipped Items =
CALCULATE ( COUNTROWS ( fact_order_item ), fact_order_item[delivery_count] > 0 )

-- OTIF % = share of shipped order items delivered complete by the requested date
OTIF % =
DIVIDE (
    CALCULATE ( SUM ( fact_order_item[otif_flag] ), fact_order_item[delivery_count] > 0 ),
    [Shipped Items]
)

-- Average order-to-delivery lead time in days (order date -> last goods issue)
Avg Lead Time (days) =
CALCULATE (
    AVERAGE ( fact_order_item[lead_time_days] ),
    fact_order_item[delivery_count] > 0
)

-- Return rate % = returned units / billed units
Return Rate % =
DIVIDE ( SUM ( fact_billing[returned_qty] ), SUM ( fact_billing[billed_qty] ) )

-- Year-over-year revenue growth (needs dim_date marked as date table)
Revenue LY =
CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_date[calendar_date] ) )

YoY Revenue % =
DIVIDE ( [Total Revenue] - [Revenue LY], [Revenue LY] )

-- Optional extras
Fill Rate % =
DIVIDE (
    CALCULATE ( SUM ( fact_order_item[delivered_qty] ), fact_order_item[delivery_count] > 0 ),
    CALCULATE ( SUM ( fact_order_item[ordered_qty] ), fact_order_item[delivery_count] > 0 )
)

Avg Invoice-to-Cash (days) =
AVERAGEX (
    FILTER (
        SUMMARIZE ( fact_billing, fact_billing[billing_id], fact_billing[days_to_cash] ),
        NOT ISBLANK ( fact_billing[days_to_cash] )
    ),
    fact_billing[days_to_cash]
)
```

## DAX vs SQL in this project
- SQL (`sql/kpi/`) computes fixed answers once, e.g. "OTIF by country" as a table.
- DAX measures are evaluated **in the filter context** of each visual: the same `OTIF %` measure
  gives the value per country, per month or per category depending on the slicers - no new query.
- `SAMEPERIODLASTYEAR` (time intelligence) replaces the SQL `LAG(net_revenue, 12)` window.
