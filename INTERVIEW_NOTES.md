# Interview notes - RetailLens (case study on real Olist data)

20 questions an interviewer may ask. Each answer points to the code. Numbers quoted in an interview
should be read from `metrics.json`, which is regenerated on every run.

### 1. What is the dataset and why did you choose it?
The Olist Brazilian E-Commerce Public Dataset (Kaggle `olistbr/brazilian-ecommerce`). It holds
about 100K real, anonymised marketplace orders from 2016-2018. Unlike most public retail data it
has the full O2C timestamp chain: purchase, payment approval, carrier hand-off, customer delivery
and the promised (estimated) date. It also has payments, reviews, products and sellers. The licence
is CC BY-NC-SA 4.0, so the project is non-commercial and gives attribution. Download:
`src/download.py`.

### 2. Walk me through the order-to-cash process.
The customer places a **sales order** (VBAK/VBAP). It is paid and approved (here the cleared
payment item is BSAD, with clearing date AUGDT). The warehouse or seller creates an **outbound
delivery** (LIKP/LIPS) and posts **goods issue** (WADAT_IST). The carrier delivers (proof of
delivery, PODAT). In a classic B2B flow, billing (VBRK/VBRP) and clearing of the receivable would
follow. Olist customers pay at checkout, so cash comes *before* shipment. That is why the cash KPI
here is approval time, not DSO.

### 3. How did you map Olist to SAP tables?
`src/sap_mapping.py` and `docs/sap_mapping.md`:
- customers -> KNA1, with `KUNNR` = `customer_unique_id`
- sellers -> LFA1
- products -> MARA, with the category as MATKL and the English texts in T023T
- orders -> VBAK, with ERDAT = purchase and VDATU = estimated delivery
- items -> VBAP
- carrier and delivery dates -> LIKP/LIPS (WADAT_IST, PODAT)
- payments -> BSAD
- reviews -> custom Z-table ZREVIEW

Fields that SAP does not have are `ZZ` append fields.

### 4. Why is KUNNR the customer_unique_id and not customer_id?
Olist creates a new `customer_id` for every order. Using it would count every order as a new
customer. `customer_unique_id` identifies the person, which is what KNA1 represents. The mapping
translates `customer_id` to the person when it fills the sold-to field (`map_to_sap`, `sold_to`).

### 5. What do VBAK, VBAP, LIKP and LIPS hold?
- **VBAK**, the order header: document number, type, created on, requested delivery date, sold-to, value.
- **VBAP**, the items: item number, material, quantity, net value.
- **LIKP**, the delivery header: planned date LFDAT, actual goods issue WADAT_IST, proof of delivery PODAT.
- **LIPS**, the delivery items: quantity LFIMG, plus a reference to the order item (VGBEL/VGPOS),
  which is the document flow.

### 6. How do you define OTIF here, and what are the limits?
`sql/05_ZC_SalesOrderItem.sql`:
- **on time** = PODAT on or before VDATU (by calendar day)
- **in full** = the order was delivered and has a delivery date
- the population is items with a final outcome: delivered, or cancelled/unavailable

Limits:
- Olist has no partial quantities, so in-full is effectively "not cancelled", and fill rate equals
  in-full at item level.
- Olist's promised dates are generous, so on-time is high. A real SAP setup would measure against
  the confirmed schedule-line date (VBEP).

### 7. How is lead time broken down?
`sql/kpi/04_lead_time_stages.sql` splits purchase -> customer into three stages: purchase ->
payment approval (hours), approval -> carrier hand-off (seller/warehouse) and carrier transit. It
shows that the North and Northeast lose their time in transit, not at the seller. That changes the
recommendation from "warehouse" to "carrier".

### 8. Olist has no returns. What did you do?
I did not invent returns. I used two clearly named proxies: the **cancellation rate**
(cancelled/unavailable items) and the **complaint rate** (orders reviewed with 1-2 stars)
(`sql/kpi/06_category_service.sql`). On a real S/4HANA system I would use return orders
(AUART RE) with order reasons (AUGRU).

### 9. Why is there no invoice-to-cash / DSO metric?
DSO measures how long receivables stay open after invoicing, under payment terms. Olist customers
pay at checkout (card, boleto, voucher), so there are no open receivables to measure. I replaced
DSO with **purchase -> payment approval** hours and the payment mix (`05_payment_types.sql`).
Boleto, a Brazilian bank slip, takes far longer to clear than cards, and that delays shipping.

### 10. Which real data-quality issues did you find?
From `src/dq.py`, run on the full data (counts are in `metrics.json > dq`):
- carrier hand-off *before* the purchase
- delivery to the customer *before* carrier hand-off
- "delivered" orders without delivery dates
- products without category, English text or dimensions
- zip prefixes missing from geolocation
- orders without items or payment
- zero-value payments
- review ids reused across orders

### 11. How did you design the DQ stage?
Each rule is one entry in `RULES`, with a type, a severity and a reason. A generic `check_table`
applies them:
- **Errors** are quarantined: the row is kept out of `cln_*` and goes to `dq_quarantine` with its
  raw JSON.
- **Warnings** are logged, and the row is kept.

Parents are checked before children, so the items of a quarantined delivery become orphans and are
quarantined too. `dq_run_log` is appended on every run, which gives a history of runs.

### 12. Why warnings instead of quarantining everything?
Quarantining a product because its category is missing would also drop its sales from revenue. That
would distort the business numbers more than the DQ issue itself. Severity separates "cannot be
trusted" (impossible dates) from "incomplete but usable" (missing category). The latter shows up as
`uncategorized`, and its complaint rate is visible in the report.

### 13. Star schema vs. normalized model - why a star here?
SAP tables are normalized for transactions. Analytics needs a clear grain and few joins:
- three facts: order item, delivery item, payment line
- four dimensions: customer, seller, material, date

Power BI's engine and DAX filter propagation are built for star schemas. The views are in
`sql/0*.sql`, and the relationships are in `powerbi/BUILD_STEPS.md`.

### 14. What are CDS views and how does your naming follow them?
Core Data Services are SAP's semantic views on HANA, with annotations for analytics, OData and
authorisations. `I_` views are interface (reusable) views, `C_` views are consumption views, and
customer objects start with Z. This project mirrors that: `ZI_Customer`, `ZI_Seller`, `ZI_Material`
and `ZI_CalendarDate`, plus `ZC_SalesOrderItem`, `ZC_DeliveryItem` and `ZC_Payment`.

### 15. Where do you use window functions?
- `RANK()` for the worst state and the most-complained category, partitioned to rank only
  categories or states with enough volume (`02`, `06`)
- `RANK() OVER (PARTITION BY segment ...)` for top-10 materials (`10`)
- `LAG(..., 1/12)` for MoM and YoY (`09`)
- a 3-month moving average (`03`)
- `SUM() OVER ()` for shares (`05`, `07`, `11`)

### 16. DAX vs SQL - when do you use which?
SQL computes fixed result sets in the database, which is reproducible and testable.
DAX measures (`powerbi/DAX_measures.md`) are evaluated in the filter context of each visual, so one
`OTIF %` measure works for any slicer combination. `SAMEPERIODLASTYEAR` replaces the SQL LAG.

### 17. How does CI work without Kaggle credentials?
`data/sample/` is a committed, deterministic slice of the real data: every order whose id starts
with "0", plus all its related rows (`src/make_sample.py`). `tests/test_mapping.py` checks that the
sampler reproduces it byte for byte. CI runs the tests on SQLite and on a PostgreSQL service
container, then runs the pipeline on the sample in PostgreSQL.

### 18. Why both PostgreSQL and SQLite?
PostgreSQL is the target (Docker and CI). SQLite lets anyone run the project with zero setup. The
same SQL runs on both thanks to three things: lower-case columns, a `stg_` prefix instead of
schemas, and three date macros (`DAYS_BETWEEN`, `HOURS_BETWEEN`, `DATE_KEY`) that `src/db.py`
translates per dialect.

### 19. How would this connect to a real S/4HANA system?
Replace `download.py` and `sap_mapping.py` with extraction of released CDS views via ODP/OData,
SAP Datasphere replication flows or SLT. Examples are `I_SalesDocumentItem`,
`I_OutboundDeliveryItem` and `I_OperationalAcctgDocItem` (for clearing). Then:
- use VBEP schedule lines for the confirmed date
- use return orders for returns, and VBRK/VBRP for billing
- keep staging, DQ, the star schema and the KPIs unchanged
- add delta loads, currency conversion and authorisations

### 20. What are the limitations of this case study?
- The SAP documents are *derived* from a marketplace dataset: one delivery per order, payments as
  cleared items, and no billing documents, schedule lines, credit memos or returns.
- The data is Brazil-only, in BRL, from 2016-2018. The fashion segment is a small part of a
  multi-category marketplace, not a fashion brand.
- Promised dates are generous.
- The licence is non-commercial.

The method transfers to a real system. The specific numbers describe Olist's marketplace.
