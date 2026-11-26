# Interview notes - RetailLens (SYNTHETIC DATA)

20 questions an interviewer may ask, each answered with a pointer to the code. Numbers quoted in
an interview should be read from `metrics.json` (they are regenerated on every run).

### 1. Walk me through the order-to-cash process.
Customer places a **sales order** (VBAK/VBAP) -> warehouse creates an **outbound delivery**
(LIKP/LIPS), picks and posts **goods issue** (WADAT_IST) -> **billing document** / invoice
(VBRK/VBRP) creates a receivable in FI -> customer **pays**, the open item is **cleared** (BSAD,
clearing date AUGDT). Returns come back as return orders (AUART 'RE'). The document flow is kept
through reference fields: LIPS.VGBEL -> order, VBRP.VGBEL -> delivery, VBRP.AUBEL -> order.
Code: the same chain is simulated in `src/generate.py::generate`.

### 2. What do VBAK and VBAP hold?
VBAK = sales document **header**: number VBELN, order type AUART, created on ERDAT, requested
delivery date VDATU, sold-to KUNNR, sales org VKORG, net value NETWR, currency WAERK.
VBAP = **items**: POSNR, material MATNR, quantity KWMENG, item net value NETWR.
Header/item is a 1:n relationship on VBELN. See `docs/data_dictionary.md`.

### 3. What do LIKP/LIPS and VBRK/VBRP hold?
LIKP = delivery header (planned date LFDAT, **actual goods issue WADAT_IST**), LIPS = delivery
items (delivered quantity LFIMG, reference to order item VGBEL/VGPOS). VBRK = billing header
(billing date FKDAT, payer, NETWR), VBRP = billing items (FKIMG, NETWR, references to delivery and
order). Revenue in this project = VBRP.NETWR (`sql/06_ZC_BillingItem.sql`).

### 4. How do you define OTIF?
On-time **and** in-full per order item: last goods-issue date <= requested delivery date VDATU
**and** delivered quantity >= ordered quantity. Computed once as `otif_flag` in
`sql/04_ZC_SalesOrderItem.sql`, aggregated in `sql/kpi/01_headline.sql` and
`02_otif_by_country.sql`. Splitting it into on-time and in-full shows *why* OTIF is missed - for the
worst country it is timing, not completeness (`reports/insights.md` finding 1).

### 5. Why measure OTIF at item level and use goods issue instead of proof of delivery?
Item level matches how customers experience shortages (one missing SKU spoils the order line).
WADAT_IST is the reliable timestamp in SD; proof-of-delivery dates need extra (often missing) data.
The trade-off is stated in the data dictionary.

### 6. How is lead time calculated?
Order creation ERDAT -> last goods issue of the item, in days, via the `DAYS_BETWEEN` macro
(`src/db.py::render_sql`), which becomes `julianday()` arithmetic on SQLite and `DATE - DATE` on
PostgreSQL.

### 7. What is invoice-to-cash and how does it relate to DSO?
Days from billing date FKDAT to clearing date AUGDT per paid invoice
(`sql/kpi/04_invoice_to_cash_by_country.sql`). DSO = receivables / revenue x days is the balance-sheet
version; invoice-to-cash is the transactional version and can be sliced by customer or country.
Unpaid invoices are reported separately as open receivables.

### 8. Star schema vs. a normalized model - why a star here?
SAP tables are normalized for transactions (header/item, many joins). Analytics wants few joins and
clear grain: facts (order item, delivery item, billing item) with measures, dimensions (customer,
material, date) to slice by. Power BI's VertiPaq engine and DAX filter propagation are designed for
star schemas. Views in `sql/0*.sql`; relationships in `powerbi/BUILD_STEPS.md`.

### 9. Why three fact tables instead of one?
Each process step has its own grain: one order item can have several deliveries (partial
deliveries) and several invoices. Forcing them into one table would duplicate quantities. The
order-item fact pre-aggregates deliveries in a CTE so OTIF stays one row per item.

### 10. Where do you use window functions and why?
`RANK()` for worst-country / top-material rankings (`02`, `04`, `06`, `10`), `RANK() OVER
(PARTITION BY category ...)` for top-3 per category, `LAG(net_revenue, 1/12)` for MoM and YoY growth
(`09`), a moving `AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` for 3-month OTIF (`03`),
and `SUM() OVER (PARTITION BY category)` for return-reason shares (`07`). They compute per-row values
against a group without collapsing rows like GROUP BY does.

### 11. RANK vs DENSE_RANK vs ROW_NUMBER?
RANK leaves gaps after ties (1,1,3), DENSE_RANK does not (1,1,2), ROW_NUMBER always unique. For
"top 3 per category" RANK keeps ties honest (two materials with equal revenue both stay).

### 12. DAX vs SQL - when do you use which?
SQL computes fixed result sets in the database (good for pipelines, tests, reuse in any tool).
DAX measures are evaluated in the **filter context** of each visual, so one `OTIF %` measure works
per country, month or category without new queries; time intelligence (`SAMEPERIODLASTYEAR`)
replaces the SQL LAG. `powerbi/DAX_measures.md` mirrors `sql/kpi/01_headline.sql` so both agree.

### 13. How did you design the data-quality stage?
Rules are data, not code: `MANDATORY`, `NON_NEGATIVE`, `REFERENCES` dicts in `src/dq.py`; one
generic `check_table` applies them. Failing rows go to `dq_quarantine` with table, key, rule, reason
and the raw record as JSON (nothing silently dropped); counts per table go to `dq_run_log` (append,
so there is history). Parents are checked before children, so items of a quarantined header become
orphans too.

### 14. How do you know the DQ checks work?
The generator injects a documented set of issues (`DQ_INJECTION`), `tests/test_generate.py`
asserts they are present, `tests/test_dq.py` asserts each rule catches its case and the cascade
works, and the pipeline log prints violations per rule.

### 15. What are CDS views?
Core Data Services: SAP's way to define semantic data models as views on the HANA database, with
annotations for analytics, OData, authorisations. Naming: `I_` interface views (reusable basic /
composite), `C_` consumption views (for a specific app/report); customer views start with Z. This
project mirrors that with `ZI_Customer`, `ZI_Material`, `ZI_CalendarDate` and `ZC_SalesOrderItem`,
`ZC_DeliveryItem`, `ZC_BillingItem`.

### 16. How would this connect to a real S/4HANA system?
Replace `src/generate.py` + CSVs with extraction of released CDS views (e.g. `I_SalesDocumentItem`,
`I_DeliveryDocumentItem`, `I_BillingDocumentItem`, `I_OperationalAcctgDocItem` for clearing) via
ODP/OData, SAP Datasphere replication flows or SLT into PostgreSQL / a warehouse; keep staging, DQ,
star schema and KPIs unchanged. In S/4HANA, BSAD is a compatibility view; the line items live in
BSEG / the Universal Journal ACDOCA.
Add delta loads (change timestamps), currency conversion (TCURR) and authorisations.

### 17. Why both PostgreSQL and SQLite?
PostgreSQL is the target (Docker, CI service container). SQLite lets anyone run it with zero setup.
Same SQL on both thanks to lower-case columns, `stg_` prefixes instead of schemas and one date macro.
CI runs the tests and the full pipeline on PostgreSQL (`.github/workflows/ci.yml`) and produces the
same headline numbers as the local SQLite run.

### 18. How do you make sure README numbers are not made up?
`src/pipeline.py::build_metrics` writes `metrics.json`; `src/render_docs.py` writes the README
metrics block and `RESUME_BULLETS.md` from it; `src/insights.py` writes the report from the KPI
tables and picks worst country/category by code.

### 19. How are the KPI queries tested?
`tests/conftest.py` holds a 2-order fixture whose answers are worked out by hand (OTIF 1/3, fill
rate 17/19, return rate 2/17 ...). `tests/test_kpi_sql.py` runs the full load -> DQ -> views -> KPI
chain on it, on SQLite and (in CI) PostgreSQL.

### 20. What are the limitations of synthetic data?
Patterns were designed in (slower transit to IT, high dress returns), so the analysis "discovers"
what the generator planted - it proves the method, not a business fact. Real data has messier
issues: changed documents, cancellations, credit memos, multiple currencies, pricing conditions,
intercompany sales and incomplete document flow. Distributions (lognormal, gamma, Pareto) are
plausible but not calibrated to a real retailer.
