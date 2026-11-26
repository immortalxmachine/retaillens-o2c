# Olist -> SAP S/4HANA SD mapping (case study)

**Data:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
by Olist, published on Kaggle under **CC BY-NC-SA 4.0** (attribution, non-commercial, share-alike).
It holds about 100K real, anonymised orders placed on Brazilian marketplaces from 2016 to 2018.

**Case-study framing:** "A Brazilian multi-category retailer's order-to-cash on SAP S/4HANA."
Olist is not an SAP system and not a fashion brand. The code in `src/sap_mapping.py` reshapes
the real data into the SD tables an SAP consultant would query, so the SQL, KPIs and dashboards
look the same as they would on a real S/4HANA extract. Every mapping assumption is listed below.
Nothing is generated: where Olist has no value, the SAP field stays empty.

## Table mapping

| Olist file | SAP table | Notes |
|---|---|---|
| `olist_customers_dataset` | **KNA1** customer master | `KUNNR` = `customer_unique_id`. Olist creates a new `customer_id` for every order, so `customer_id` is translated to the person (`customer_unique_id`) when it becomes the sold-to on VBAK/LIKP/BSAD |
| `olist_sellers_dataset` | **LFA1** vendor master | Marketplace sellers play the role of the supplying vendors |
| `olist_products_dataset` | **MARA** material master | `MATKL` = Olist category code (Portuguese). Weight and dimensions go to `BRGEW` and `LAENG`/`BREIT`/`HOEHE`. There is no MAKT: Olist publishes no product names |
| `product_category_name_translation` | **T023T** material group texts | `WGBEZ` = English category name (`SPRAS` = E) |
| `olist_orders_dataset` | **VBAK** sales order header | See the field table below |
| `olist_order_items_dataset` | **VBAP** sales order item | One Olist item row = one piece (`KWMENG` = 1). `NETWR` = price, `ZZFREIGHT` = freight |
| orders + items | **LIKP / LIPS** outbound delivery | One delivery per order (Olist records one carrier hand-off and one delivery date per order). Created when the order was handed to the carrier, delivered, or has status shipped/delivered |
| `olist_order_payments_dataset` | **BSAD** cleared customer items | One line per payment. `AUGDT` = the order's payment approval timestamp |
| `olist_order_reviews_dataset` | **ZREVIEW** (custom Z-table) | SD has no standard review table, so this is a customer-specific Z-table |
| `olist_geolocation_dataset` | **ZGEO** (custom Z-table) | One row per 5-digit zip prefix (mean lat/lng, most frequent state). Used for the zip-code DQ check |

## Field mapping (order-to-cash dates)

| SAP field | Meaning in SAP | Olist source |
|---|---|---|
| VBAK.ERDAT | Created on | `order_purchase_timestamp` (date and time) |
| VBAK.VDATU | Requested delivery date | `order_estimated_delivery_date`, the date promised to the customer at checkout |
| VBAK.ZZSTATUS | (Z-field) order status | `order_status` (delivered, shipped, canceled, unavailable, invoiced, processing, created, approved) |
| BSAD.AUGDT | Clearing date | `order_approved_at`, when the payment was approved |
| LIPS.WADAT | Planned goods issue (here per item) | `shipping_limit_date`, the seller's ship-by date |
| LIKP.WADAT_IST | Actual goods issue | `order_delivered_carrier_date`, the carrier hand-off |
| LIKP.PODAT | Proof-of-delivery date | `order_delivered_customer_date` |
| LIKP.LFDAT | Planned delivery date | `order_estimated_delivery_date` |
| BSAD.ZLSCH | Payment method | `payment_type` (credit_card, boleto, voucher, debit_card) |
| BSAD.ZZINSTALLMENTS | (Z-field) instalments | `payment_installments` |

Fields starting with **ZZ** are customer extensions (the usual SAP convention for append fields).

## KPI definitions and their limits

- **On time:** `PODAT <= VDATU`, compared on calendar days. Olist's estimated dates are generous
  (compare `avg_promised_days` with `avg_lead_time_days` in `metrics.json`), so on-time looks high. A stricter internal
  SLA would show more lateness.
- **In full:** the order reached `delivered` with a proof-of-delivery date. Olist has no
  partial-delivery quantities: an item is either delivered or its order is cancelled/unavailable.
  This makes **fill rate equal to the in-full rate** at item level.
- **OTIF population:** order items with a final outcome, meaning delivered with a date, or
  cancelled/unavailable. Orders still in process at the end of the extract are excluded, and so
  are deliveries quarantined by DQ.
- **Returns:** Olist has **no returns table**, and none are invented. Two honest proxies are used
  instead: the **cancellation rate** (cancelled/unavailable items) and the **complaint rate**
  (orders reviewed with 1-2 stars).
- **Invoice-to-cash / DSO:** Olist customers pay at checkout (card, boleto, voucher), and there are
  no invoices with payment terms. A DSO-style metric would therefore be meaningless. It is replaced
  by **purchase -> payment approval time** and the **payment-type / instalment mix**.
- **Analysis window:** 2017-01-01 to 2018-08-31 (complete months). 2016 holds a few hundred test
  orders, and September/October 2018 hold mostly unfinished orders.
