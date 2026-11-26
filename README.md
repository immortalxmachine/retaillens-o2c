# RetailLens - SAP S/4HANA Order-to-Cash Case Study on Real Retail Orders

![RetailLens Streamlit dashboard demo](docs/screenshots/demo.gif)

[![CI](https://github.com/immortalxmachine/retaillens-o2c/actions/workflows/ci.yml/badge.svg)](https://github.com/immortalxmachine/retaillens-o2c/actions/workflows/ci.yml)

> **Case study: a Brazilian multi-category retailer's order-to-cash on SAP S/4HANA.**
> The data is **real**: the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
> (about 100K anonymised orders, 2016-2018, by Olist on Kaggle). Licence: **CC BY-NC-SA 4.0**,
> so it may be used **non-commercially** only, with attribution, and shared under the same licence.
> Olist is a marketplace, not an SAP system and not a fashion brand. This project maps its tables
> into SAP SD structures (KNA1, MARA/T023T, VBAK/VBAP, LIKP/LIPS, BSAD) and analyses a
> fashion & accessories segment separately for a fashion-retail client. See
> [docs/sap_mapping.md](docs/sap_mapping.md) for every mapping assumption.

RetailLens takes order-to-cash (O2C) data from raw extracts to business decisions. The steps are:
- Kaggle download and SAP-structure mapping
- staging load
- data-quality gates that quarantine **real** inconsistencies
- a star schema built as CDS-style SQL views
- O2C KPIs in SQL (CTEs and window functions)
- a Power BI model with DAX measures
- a Streamlit dashboard
- a one-page consultant report

## Architecture

```mermaid
flowchart LR
    K[Kaggle: Olist CSVs<br/>CC BY-NC-SA 4.0] -->|src/download.py| RAW[data/raw]
    RAW -->|src/sap_mapping.py| SAP
    subgraph SAP["SAP S/4HANA SD structures"]
        KNA1[KNA1 / LFA1]
        MARA[MARA / T023T]
        VBAK[VBAK / VBAP orders]
        LIKP[LIKP / LIPS deliveries]
        BSAD[BSAD payments, ZREVIEW]
    end
    SAP -->|src/load.py| STG[(staging stg_*<br/>PostgreSQL / SQLite)]
    STG -->|src/dq.py rules| DQ{Data quality}
    DQ -->|pass / warning| CLN[(clean cln_*)]
    DQ -->|error + reason| Q[(dq_quarantine<br/>dq_run_log)]
    CLN -->|sql/0*.sql| STAR[Star schema views<br/>ZC_SalesOrderItem, ZC_DeliveryItem, ZC_Payment<br/>ZI_Customer, ZI_Seller, ZI_Material, ZI_CalendarDate]
    STAR -->|sql/kpi/*.sql| KPI[(kpi_* tables<br/>metrics.json)]
    STAR -->|src/export_powerbi.py| PBI[Power BI<br/>CSV/Parquet + DAX]
    KPI --> ST[Streamlit dashboard :8530]
    KPI --> REP[reports/insights.md<br/>charts]
```

## Key metrics (latest full run)

<!-- METRICS:START -->
_From `metrics.json` (run on sqlite, full Kaggle download) - real Olist data, CC BY-NC-SA 4.0._

| Metric | Value |
|---|---|
| Source rows (9 Olist CSVs) | 1,550,922 |
| Orders / order items in analysis window | 98,353 / 112,279 (2017-01-01 to 2018-08-31) |
| Customers / sellers | 95,121 / 3,068 |
| Rows checked by DQ / quarantined / warnings | 775,547 / 444 / 3,288 |
| Net revenue (non-cancelled items) | BRL 13.45M |
| Revenue growth 2018 vs 2017 (months 01-08) | 138.3% |
| OTIF (on-time in-full) | 92.9% |
| Avg order-to-delivery lead time (promised) | 12.4 days (24.3) |
| Cancellation rate (items) | 0.48% |
| Complaint rate (review 1-2 stars) | 14.2% |
| Avg purchase-to-payment-approval | 10.3 hours |
| Fashion & accessories share of revenue | 11.4% |
<!-- METRICS:END -->

Five findings with recommendations: **[reports/insights.md](reports/insights.md)**.

## Screenshots

| | |
|---|---|
| ![KPI overview](docs/screenshots/01-overview.png) | ![Drill-down](docs/screenshots/02-drilldown.png) |
| **KPI overview**: headline O2C KPIs, monthly revenue, the 10 worst states by OTIF, complaint rate by category | **Drill-down**: Northeast Brazil, fashion & accessories segment: OTIF by state, revenue by month, category table |
| ![Data quality](docs/screenshots/03-data-quality.png) | ![Pipeline run](docs/screenshots/05-pipeline-run.png) |
| **Data quality**: real issues by rule, errors quarantined vs warnings logged, raw records as JSON | **Pipeline run**: real terminal output of `python -m src.pipeline` on the full dataset |
| ![CI passing](docs/screenshots/06-ci-passing.png) | **Power BI**: `docs/screenshots/04-powerbi.png` is **pending**. The `.pbix` is built by hand in Power BI Desktop, following [powerbi/BUILD_STEPS.md](powerbi/BUILD_STEPS.md). |
| **CI**: ruff, then pytest on SQLite and PostgreSQL, then the pipeline on the committed real sample in PostgreSQL, then a Docker build | |

KPI charts saved from code (`src/charts.py`):

| | |
|---|---|
| ![OTIF by state](reports/charts/otif_by_state.png) | ![Complaints late vs on time](reports/charts/complaints_late_vs_on_time.png) |
| ![Lead time stages](reports/charts/lead_time_stages.png) | ![Complaints by category](reports/charts/complaints_by_category.png) |
| ![Monthly revenue](reports/charts/revenue_monthly.png) | |

## What is in the repo

| Path | What it does |
|---|---|
| `src/download.py` | Downloads Olist from Kaggle with the Kaggle CLI (your own credentials; never stored here) |
| `src/sap_mapping.py` | Maps the 9 Olist CSVs to SAP tables (KNA1, LFA1, MARA, T023T, VBAK, VBAP, LIKP, LIPS, BSAD, ZREVIEW, ZGEO) |
| `src/make_sample.py`, `data/sample/` | Deterministic real sample (orders with ids starting with `0`) for CI and tests |
| `src/load.py` | Loads the SAP tables into `stg_*` staging tables |
| `src/dq.py` | Rules (mandatory, non-negative, reference, consistency) with error/warning severity -> `cln_*`, `dq_quarantine`, `dq_run_log` |
| `sql/0*.sql` | Star schema as CDS-style views (`ZI_*` interface, `ZC_*` consumption) |
| `sql/kpi/*.sql` | OTIF by state, lead-time stages, payment approval, complaints vs delivery, category service, revenue MoM/YoY (LAG), top-N (RANK) |
| `src/kpis.py` | Runs the KPI SQL and stores `kpi_*` tables and `reports/kpi/*.csv` |
| `src/export_powerbi.py`, `powerbi/` | Star schema export, `DAX_measures.md`, `BUILD_STEPS.md` |
| `app/streamlit_app.py` | Dashboard: KPI overview, drill-down, data quality |
| `src/insights.py` | Writes `reports/insights.md` from the KPI tables |
| `src/render_docs.py` | Writes the numbers above and `RESUME_BULLETS.md` from `metrics.json` |
| `src/pipeline.py` | Runs everything end to end |
| `tests/` | Mapping, DQ rules, sample determinism, KPI SQL on a hand-checked fixture (SQLite and PostgreSQL) |
| `docs/` | `sap_mapping.md` (mapping and KPI limits), `data_dictionary.md` |
| `INTERVIEW_NOTES.md` | 20 interview Q&As tied to the code |

## How to run

**Local (SQLite, no Docker needed)**, with Python 3.11 or newer:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
# Kaggle credentials: https://www.kaggle.com/docs/api (stored in your home folder, not in the repo)
python -m src.pipeline            # download -> map -> load -> DQ -> star schema -> KPIs -> exports
streamlit run app/streamlit_app.py --server.port 8530
pytest && ruff check .
```

To run without Kaggle credentials, use the committed real sample:
`RETAILLENS_RAW_DIR=data/sample python -m src.pipeline`.

**PostgreSQL**: set `DATABASE_URL` (see `.env.example`), for example
`postgresql+psycopg2://retaillens:change_me@localhost:5440/retaillens`, then run the same commands.

**Docker** (PostgreSQL on host port 5440, Streamlit on 8530). It uses the committed real sample by
default. To use the full data, run `python -m src.download` and set `RETAILLENS_RAW_DIR=data/raw`
in `.env`:

```bash
cp .env.example .env              # set your own password
docker compose up --build         # db -> pipeline (one-off) -> dashboard at http://localhost:8530
```

## Limitations
- This is a case study: Olist is a marketplace, so SAP documents are *derived* from its tables.
  There is one delivery per order, and payments are mapped to cleared items. Fields that do not
  exist in SAP are marked `ZZ`.
- There is no returns table. The cancellation rate and the 1-2 star complaint rate are used as
  proxies, and no returns are invented.
- Customers pay at checkout, so there is no invoice-to-cash/DSO metric. Payment-approval time and
  the payment mix replace it.
- Olist's promised dates are generous, which keeps the on-time rate high. A stricter internal SLA
  would show more lateness.
- Licence CC BY-NC-SA 4.0: non-commercial use only. Derived outputs in this repo (sample, charts,
  KPI tables) are shared under the same licence.
