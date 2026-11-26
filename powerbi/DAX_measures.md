# DAX measures - RetailLens case study (real Olist data, CC BY-NC-SA 4.0)

Create these in Power BI Desktop (Modeling > New measure). They mirror the SQL definitions in
`sql/kpi/01_headline.sql`, so the Power BI numbers should match `metrics.json > headline`.

Tables come from `powerbi/data/` (see `BUILD_STEPS.md`): `fact_order_item`, `fact_delivery`,
`fact_payment`, `dim_customer`, `dim_seller`, `dim_material`, `dim_date`.
Filter the report to `dim_date[in_analysis_window] = 1` (page or report filter).

```DAX
-- Revenue = item price of orders that were not cancelled (freight reported separately)
Total Revenue =
CALCULATE ( SUM ( fact_order_item[item_value] ), fact_order_item[cancelled_flag] = 0 )

-- OTIF population: items with a final outcome (delivered with a date, or cancelled)
Eligible Items =
CALCULATE ( COUNTROWS ( fact_order_item ), fact_order_item[otif_eligible] = 1 )

-- OTIF % = delivered complete AND on or before the promised date (VBAK.VDATU)
OTIF % =
DIVIDE (
    CALCULATE ( SUM ( fact_order_item[otif_flag] ), fact_order_item[otif_eligible] = 1 ),
    [Eligible Items]
)

-- Average order-to-delivery lead time in days (purchase -> received)
Avg Lead Time (days) =
CALCULATE ( AVERAGE ( fact_order_item[lead_time_days] ), fact_order_item[in_full_flag] = 1 )

-- Olist has no returns table: two honest proxies replace "Return Rate %"
Cancellation Rate % =
DIVIDE (
    CALCULATE ( SUM ( fact_order_item[cancelled_flag] ), fact_order_item[otif_eligible] = 1 ),
    [Eligible Items]
)

-- Complaint rate at order level: share of reviewed orders with a 1-2 star review
Complaint Rate % =
VAR ReviewedOrders =
    CALCULATETABLE (
        SUMMARIZE ( fact_order_item, fact_order_item[order_id],
                    "low", MAX ( fact_order_item[low_review_flag] ) ),
        fact_order_item[has_review] = 1
    )
RETURN
    DIVIDE ( COUNTROWS ( FILTER ( ReviewedOrders, [low] = 1 ) ), COUNTROWS ( ReviewedOrders ) )

-- Cash side: hours from purchase to payment approval (order level)
Avg Approval Hours =
AVERAGEX (
    SUMMARIZE ( fact_payment, fact_payment[order_id],
                "h", MAX ( fact_payment[approval_hours] ) ),
    [h]
)

-- Year-over-year revenue growth (needs dim_date marked as date table)
Revenue LY =
CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_date[calendar_date] ) )

YoY Revenue % =
DIVIDE ( [Total Revenue] - [Revenue LY], [Revenue LY] )
```

## DAX vs SQL in this project
- SQL (`sql/kpi/`) computes fixed answers once, for example "OTIF by state" as a table.
- DAX measures are evaluated **in the filter context** of each visual. The same `OTIF %` measure
  gives the value per state, month or segment, depending on the slicers, without a new query.
- `SAMEPERIODLASTYEAR` (time intelligence) replaces the SQL `LAG(net_revenue, 12)` window.
