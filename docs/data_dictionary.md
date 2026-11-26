# Data dictionary - RetailLens (case study on real Olist data)

Source: Olist Brazilian E-Commerce Public Dataset (Kaggle `olistbr/brazilian-ecommerce`,
CC BY-NC-SA 4.0, non-commercial use). The mapping from Olist files to SAP tables, and its
assumptions, are described in [`sap_mapping.md`](sap_mapping.md). Exact row counts of the latest
run are in `metrics.json` (`source_row_counts`, `sap_row_counts`, `star_schema_row_counts`).

## SAP-structured tables (staging `stg_*`, clean `cln_*`)

### KNA1 - customer master
| Field | Meaning |
|---|---|
| KUNNR | Customer number (Olist `customer_unique_id`, 32-char hash) |
| LAND1 | Country key (BR) |
| REGIO | Region = Brazilian state (SP, RJ, MG, ...) |
| ORT01 | City |
| PSTLZ | Postal code (first 5 digits = Olist zip prefix) |

### LFA1 - vendor master (marketplace sellers)
| Field | Meaning |
|---|---|
| LIFNR | Vendor (seller) number |
| LAND1 / REGIO / ORT01 / PSTLZ | Country, state, city, zip prefix |

### MARA - material master / T023T - material group texts
| Field | Meaning |
|---|---|
| MATNR | Material number (Olist `product_id`) |
| MATKL | Material group = product category code (Portuguese). Missing for some products in the source (count in `metrics.json`) |
| MTART | Material type (HAWA = trading goods) |
| BRGEW / GEWEI | Gross weight / unit (G) |
| LAENG / BREIT / HOEHE / MEABM | Length / width / height / unit (CM) |
| T023T.WGBEZ | English category text (`SPRAS` = E) |

### VBAK - sales order header / VBAP - sales order item
| Field | Meaning |
|---|---|
| VBELN | Sales document number (Olist `order_id`) |
| AUART | Order type (OR) |
| ERDAT | Created on = purchase timestamp |
| VDATU | Requested delivery date = estimated (promised) delivery date |
| KUNNR | Sold-to customer |
| ZZSTATUS | Order status from Olist (Z-field) |
| NETWR / WAERK | Net value / currency (BRL) |
| POSNR (VBAP) | Item number |
| MATNR (VBAP) | Material |
| ZZLIFNR (VBAP) | Seller of the item (Z-field) |
| KWMENG / VRKME (VBAP) | Quantity (1 per Olist item row) / unit |
| NETWR (VBAP) | Item price |
| ZZFREIGHT (VBAP) | Freight charged for the item (Z-field) |

### LIKP - delivery header / LIPS - delivery item
| Field | Meaning |
|---|---|
| VBELN | Delivery number (= order number, one consignment per order) |
| KUNNR | Ship-to customer |
| LFDAT | Planned delivery date (= promised date) |
| WADAT_IST | **Actual goods issue** = carrier hand-off |
| PODAT | **Proof of delivery** = received by the customer |
| POSNR / MATNR (LIPS) | Delivery item / material |
| LFIMG (LIPS) | Delivered quantity |
| VGBEL / VGPOS (LIPS) | Reference sales order / item (document flow) |
| WADAT (LIPS) | Seller ship-by date (planned goods issue per item) |
| ZZLIFNR (LIPS) | Seller |

### BSAD - cleared customer items (payments)
| Field | Meaning |
|---|---|
| BELNR | Payment document (`order_id` + payment sequence) |
| VBELN | Sales order that was paid |
| KUNNR | Customer |
| ZLSCH | Payment method (credit_card, boleto, voucher, debit_card, not_defined) |
| ZZINSTALLMENTS | Number of instalments (Z-field) |
| DMBTR / WAERS | Amount / currency (BRL) |
| AUGDT | Clearing date = payment approval timestamp |

### ZREVIEW - customer reviews (custom) / ZGEO - zip geolocation (custom)
| Field | Meaning |
|---|---|
| REVIEW_ID / VBELN | Review id / order |
| SCORE | 1-5 stars |
| CREATED / ANSWERED | Survey sent / answered |
| HAS_COMMENT | 1 if the customer wrote a comment (the text itself is not used) |
| ZGEO.PSTLZ / LAT / LNG / REGIO | Zip prefix, mean coordinates, state |

## Real data-quality issues found by `src/dq.py`

Errors are **quarantined** (kept out of `cln_*`). Warnings are **logged**, and the row is kept.
The counts from the latest full run are listed in `metrics.json > dq.issues_by_reason`:

| Severity | Issue |
|---|---|
| error | Delivery handed to the carrier before the order was placed (WADAT_IST < ERDAT) |
| error | Delivered to the customer before carrier hand-off (PODAT < WADAT_IST) |
| error | Status "delivered" but no delivery date / no carrier date |
| error | Delivery items of a quarantined delivery (orphans of LIKP) |
| warning | Products without category, without English category text, or without weight/dimensions |
| warning | Customer / seller zip prefixes missing from the geolocation table |
| warning | Orders without items, orders without payment, payments of zero value |
| warning | The same review id used for more than one order |

## Star schema (views in `sql/`, exported to `powerbi/data/`)
| Logical name | View | Grain | Key measures / flags |
|---|---|---|---|
| dim_customer | ZI_Customer | customer | state, macro_region, city |
| dim_seller | ZI_Seller | seller | state, city |
| dim_material | ZI_Material | material | category (English), segment (Fashion & accessories / Other), weight, volume |
| dim_date | ZI_CalendarDate | day | date_key, month_key, is_festive, in_analysis_window |
| fact_order_item | ZC_SalesOrderItem | order item | item_value, freight, otif/on-time/in-full flags, lead-time stages, review score |
| fact_delivery | ZC_DeliveryItem | delivery item | handover delay vs ship-by date, transit days, days vs promise |
| fact_payment | ZC_Payment | payment line | payment type, instalments, amount, approval hours |

## KPI definitions (`sql/kpi/*.sql`)
- **OTIF** = item delivered (in full) **and** received on or before VDATU, over items with a final outcome.
- **Lead time** = purchase -> customer delivery in calendar days. It is split into approval
  (hours), approval -> goods issue, and transit.
- **Cancellation rate** = items in cancelled/unavailable orders. **Complaint rate** = reviewed orders with 1-2 stars.
- **Payment approval time** = purchase -> `AUGDT` in hours, by payment type.
- **Revenue** = item price of non-cancelled orders (freight reported separately). **MoM / YoY** via LAG.
- Details and limitations: [`sap_mapping.md`](sap_mapping.md).
