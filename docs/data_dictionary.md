# Data dictionary - RetailLens (SYNTHETIC DATA)

All data is **synthetic**, produced by the seeded generator `src/generate.py` (seed 42 by default).
Tables and fields follow SAP S/4HANA Sales & Distribution (SD) naming so the SQL reads like it
would on a real system. Exact row counts of the latest run are in `metrics.json`
(`raw_row_counts`, `star_schema_row_counts`).

Business story: a European fashion wholesaler selling to ~400 retail stores (B2B) in DE, FR, IT,
ES and NL, orders from 2023-01-01 to 2024-12-31, extract date 2025-02-15.

## Source tables (raw extracts in `data/raw/*.csv`, staging tables `stg_*`)

### KNA1 - customer master
| Field | Meaning |
|---|---|
| KUNNR | Customer number (10 digits, zero-padded) |
| NAME1 | Customer name |
| LAND1 | Country key (DE, FR, IT, ES, NL) |
| REGIO | Region within the country (e.g. BY, LOM, IDF) |

### MARA - material master / MAKT - material descriptions
| Field | Meaning |
|---|---|
| MATNR | Material number |
| MATKL | Material group = product category (TOPS, DRESSES, DENIM, KNITWEAR, OUTERWEAR, FOOTWEAR, ACCESSORIES, ACTIVEWEAR) |
| SAISO | Season indicator (SS spring/summer, AW autumn/winter, CORE all year) - as in SAP Fashion Management |
| MTART | Material type (FERT = finished product) |
| MAKTX (MAKT) | Material description |
| SPRAS (MAKT) | Language key (E = English) |

### VBAK - sales order header / VBAP - sales order item
| Field | Meaning |
|---|---|
| VBELN | Sales document number |
| AUART | Order type (OR = standard order) |
| ERDAT | Created on (order date) |
| VDATU | Requested delivery date (basis for "on time") |
| KUNNR | Sold-to customer |
| VKORG | Sales organisation |
| NETWR / WAERK | Net value / currency (EUR) |
| POSNR (VBAP) | Item number (10, 20, 30 ...) |
| MATNR (VBAP) | Material |
| KWMENG (VBAP) | Order quantity |
| VRKME (VBAP) | Sales unit (PC) |

### LIKP - delivery header / LIPS - delivery item
| Field | Meaning |
|---|---|
| VBELN | Delivery number |
| ERDAT | Delivery created on |
| LFDAT | Planned delivery date (= requested date) |
| WADAT_IST | **Actual goods-issue date** - when the goods left the warehouse |
| POSNR / MATNR (LIPS) | Delivery item / material |
| LFIMG (LIPS) | Delivered quantity |
| VGBEL / VGPOS (LIPS) | Reference sales order / order item (document flow) |

### VBRK - billing header / VBRP - billing item
| Field | Meaning |
|---|---|
| VBELN | Billing document (invoice) number |
| FKART | Billing type (F2 = invoice) |
| FKDAT | Billing date |
| KUNAG | Sold-to party |
| NETWR | Net value = **revenue** |
| FKIMG (VBRP) | Billed quantity |
| VGBEL / VGPOS (VBRP) | Reference delivery / delivery item |
| AUBEL / AUPOS (VBRP) | Reference sales order / order item |

### BSAD - cleared customer items (payments)
| Field | Meaning |
|---|---|
| BELNR | Accounting (payment) document |
| KUNNR | Customer |
| VBELN | Billing document that was paid |
| AUGDT | **Clearing date** = date the invoice was paid |
| DMBTR / WAERS | Amount / currency |

Invoices without a BSAD row are still open (unpaid) at extract date.

### RETURNS - return order items (modelled on VBAK/VBAP with AUART = 'RE')
| Field | Meaning |
|---|---|
| VBELN / POSNR | Return order / item |
| AUART | RE = return order |
| ERDAT | Return created on |
| MATNR / KWMENG / NETWR | Material / returned quantity / returned value |
| AUGRU | Order reason: R01 size/fit, R02 quality defect, R03 not as described, R04 delivered too late |
| VGBEL / VGPOS | Reference billing document / item |

## Simulated business patterns
- **Seasons**: SS collections dominate Feb-Jul orders, AW collections Aug-Jan.
- **Festive peak**: order intake x2.2 from 10 Nov to 20 Dec; launch peaks in March and September; summer lull in August; ~12% yearly growth.
- **Partial deliveries**: ~6% of items ship in two deliveries (backorder 5-15 days later), ~2.5% are short-shipped; footwear (x2.2) and denim (x1.6) run out of sizes more often.
- **Late deliveries**: transit time differs by country (IT +3 days, ES +2, FR +1) and grows by 2 days in the festive peak.
- **Returns**: probability per billed line depends on category (dresses 20%, footwear 16%, accessories 3% ...) and rises by 5 points after a late delivery.
- **Payments**: terms 30 or 60 days; each customer has a payment habit; IT/ES customers pay later; ~2% of invoices stay open.

## Injected data-quality issues (documented, `DQ_INJECTION` in `src/generate.py`)
| Issue | Table | Count | Caught by rule |
|---|---|---|---|
| Missing creation date ERDAT | VBAK | 12 | mandatory |
| Negative order quantity KWMENG | VBAP | 25 | non_negative |
| Orphan items (VBELN not in VBAK) | VBAP | 20 | reference |
| Missing goods-issue date WADAT_IST | LIKP | 10 | mandatory |
| Orphan delivery items (VBELN not in LIKP) | LIPS | 15 | reference |

Because parents are cleaned before children, items belonging to a quarantined header are also
quarantined (e.g. VBAP items of the 12 orders without ERDAT). That is why the quarantine count is
larger than the 82 injected issues - see `dq` in `metrics.json`.

## Star schema (views in `sql/`, exported to `powerbi/data/`)
| Logical name | View | Grain | Key measures / flags |
|---|---|---|---|
| dim_customer | ZI_Customer | customer | country, region |
| dim_material | ZI_Material | material | category, season, name |
| dim_date | ZI_CalendarDate | day | month_key, season_half, is_festive |
| fact_order_item | ZC_SalesOrderItem | order item | ordered/delivered qty, lead_time_days, on_time_flag, in_full_flag, otif_flag |
| fact_delivery | ZC_DeliveryItem | delivery item | delivered_qty, days_late, late_flag |
| fact_billing | ZC_BillingItem | billing item | net_revenue, days_to_cash, returned_qty |

## KPI definitions (`sql/kpi/*.sql`)
- **Lead time** = days from order creation (VBAK.ERDAT) to the last goods issue of the item (LIKP.WADAT_IST).
- **On time** = last goods issue <= requested delivery date (VBAK.VDATU). **In full** = delivered qty >= ordered qty. **OTIF** = both. Measured on order items with at least one delivery.
- **Fill rate** = delivered qty / ordered qty.
- **Invoice-to-cash days** = clearing date (BSAD.AUGDT) - billing date (VBRK.FKDAT), per paid invoice (DSO-style).
- **Return rate** = returned qty / billed qty.
- **Revenue** = VBRP.NETWR; **MoM / YoY growth** via LAG over monthly revenue.
