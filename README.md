# RetailLens - SAP S/4HANA Order-to-Cash Analytics for Fashion Retail

![RetailLens Streamlit dashboard demo](docs/screenshots/demo.gif)

[![CI](https://github.com/immortalxmachine/retaillens-o2c/actions/workflows/ci.yml/badge.svg)](https://github.com/immortalxmachine/retaillens-o2c/actions/workflows/ci.yml)

> **SYNTHETIC DATA.** No public S/4HANA dataset exists, so every row here comes from a seeded
> generator (`src/generate.py`) that writes a fashion wholesaler's sales data in **SAP S/4HANA SD
> table structures** (KNA1, MARA/MAKT, VBAK/VBAP, LIKP/LIPS, VBRK/VBRP, BSAD, return orders).
> Numbers show the method, not a real company.

RetailLens takes order-to-cash (O2C) data from raw SAP-style extracts to business decisions:
staging load, data-quality gates with a quarantine table, a star schema built as CDS-style SQL views,
O2C KPIs in SQL (CTEs + window functions), a Power BI model with DAX measures, a Streamlit dashboard
and a one-page consultant report.

## Architecture

```mermaid
flowchart LR
    subgraph SAP["SAP S/4HANA SD tables (SYNTHETIC)"]
        KNA1[KNA1 customers]
        MARA[MARA/MAKT materials]
        VBAK[VBAK/VBAP sales orders]
        LIKP[LIKP/LIPS deliveries]
        VBRK[VBRK/VBRP billing]
        BSAD[BSAD payments + returns]
    end
    SAP -->|src/generate.py + src/load.py| STG[(staging stg_*<br/>PostgreSQL / SQLite)]
    STG -->|src/dq.py rules| DQ{Data quality}
    DQ -->|pass| CLN[(clean cln_*)]
    DQ -->|fail + reason| Q[(dq_quarantine<br/>dq_run_log)]
    CLN -->|sql/0*.sql| STAR[Star schema views<br/>ZC_SalesOrderItem, ZC_DeliveryItem, ZC_BillingItem<br/>ZI_Customer, ZI_Material, ZI_CalendarDate]
    STAR -->|sql/kpi/*.sql| KPI[(kpi_* tables<br/>metrics.json)]
    STAR -->|src/export_powerbi.py| PBI[Power BI<br/>CSV/Parquet + DAX]
    KPI --> ST[Streamlit dashboard :8530]
    KPI --> REP[reports/insights.md<br/>charts]
```

## Key metrics (latest run)

<!-- METRICS:START -->
_From `metrics.json` (run on sqlite, seed 42) - SYNTHETIC DATA._

| Metric | Value |
|---|---|
| Customers (KNA1) | 400 |
| Materials (MARA) | 1,500 |
| Sales orders / order items (clean) | 12,488 / 32,122 |
| Delivery items (LIPS) / billing items (VBRP) | 34,575 / 34,560 |
| Rows checked by DQ / quarantined | 164,797 / 136 |
| Net revenue | EUR 17.32M |
| Revenue growth 2024 vs 2023 | 20.0% |
| OTIF (on-time in-full) | 74.0% |
| Avg order-to-delivery lead time | 5.6 days |
| Fill rate | 98.9% |
| Return rate (units) | 4.9% |
| Avg invoice-to-cash | 38.1 days |
<!-- METRICS:END -->

Five findings with recommendations: **[reports/insights.md](reports/insights.md)**.

## Screenshots

| | |
|---|---|
| ![KPI overview](docs/screenshots/01-overview.png) | ![Drill-down](docs/screenshots/02-drilldown.png) |
| **KPI overview** - headline O2C KPIs, monthly revenue, OTIF by country, return rate by category | **Drill-down** - filtered to Italy, dresses + footwear: OTIF by region, order value by month, top materials |
| ![Data quality](docs/screenshots/03-data-quality.png) | ![Pipeline run](docs/screenshots/05-pipeline-run.png) |
| **Data quality** - rows checked/passed/quarantined, violations by rule, quarantined records with raw JSON | **Pipeline run** - real terminal output of `python -m src.pipeline` |
| ![CI passing](docs/screenshots/06-ci-passing.png) | **Power BI** - `docs/screenshots/04-powerbi.png` is **pending**: the `.pbix` is built by hand in Power BI Desktop following [powerbi/BUILD_STEPS.md](powerbi/BUILD_STEPS.md). |
| **CI** - ruff, pytest on SQLite + PostgreSQL, full pipeline on PostgreSQL, Docker build | |

KPI charts saved from code (`src/charts.py`):

| | |
|---|---|
| ![OTIF by country](reports/charts/otif_by_country.png) | ![Return rate by category](reports/charts/return_rate_by_category.png) |
| ![Invoice to cash](reports/charts/invoice_to_cash_by_country.png) | ![Monthly revenue](reports/charts/revenue_monthly.png) |

## What is in the repo

| Path | What it does |
|---|---|
| `src/generate.py` | Seeded synthetic data in SAP SD structures; seasons, festive peak, partial/late deliveries, returns, payments; injects documented DQ issues |
| `src/load.py` | Loads raw extracts into `stg_*` staging tables |
| `src/dq.py` | Mandatory / non-negative / referential-integrity rules -> `cln_*`, `dq_quarantine`, `dq_run_log` |
| `sql/0*.sql` | Star schema as CDS-style views (`ZI_*` interface, `ZC_*` consumption) |
| `sql/kpi/*.sql` | O2C KPIs: OTIF, lead time, fill rate, invoice-to-cash, return rate, revenue by region/season/category, MoM/YoY (LAG), top-N (RANK) |
| `src/kpis.py` | Runs the KPI SQL, stores `kpi_*` tables and `reports/kpi/*.csv` |
| `src/export_powerbi.py`, `powerbi/` | Star schema export (CSV + Parquet), `DAX_measures.md`, `BUILD_STEPS.md` |
| `app/streamlit_app.py` | Dashboard: KPI overview, drill-down, data quality |
| `src/insights.py` | Writes `reports/insights.md` from the KPI tables |
| `src/render_docs.py` | Writes the numbers above and `RESUME_BULLETS.md` from `metrics.json` |
| `src/pipeline.py` | Runs everything end to end |
| `tests/` | Generator determinism, DQ rules, KPI SQL on a hand-checked fixture (SQLite + PostgreSQL) |
| `docs/data_dictionary.md` | SAP fields, simulated patterns, injected DQ issues, KPI definitions |
| `INTERVIEW_NOTES.md` | 20 interview Q&As tied to the code |

## How to run

**Local (SQLite, no Docker needed)** - Python 3.11+:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
python -m src.pipeline            # generate -> load -> DQ -> star schema -> KPIs -> exports
streamlit run app/streamlit_app.py --server.port 8530
pytest && ruff check .
```

**PostgreSQL** - set `DATABASE_URL` (see `.env.example`), e.g.
`postgresql+psycopg2://retaillens:change_me@localhost:5440/retaillens`, then run the same commands.

**Docker** (PostgreSQL on host port 5440, Streamlit on 8530):

```bash
cp .env.example .env              # set your own password
docker compose up --build         # db -> pipeline (one-off) -> dashboard at http://localhost:8530
```

CI (GitHub Actions) runs ruff, the tests on SQLite **and** a PostgreSQL service container, the
full pipeline on PostgreSQL, and a Docker image build.

## Limitations
- The data is synthetic: patterns were designed in (e.g. slower transit to IT), so the "findings"
  validate the analytics, not a real business.
- One currency (EUR), one sales organisation, no pricing conditions (KONV/PRCD_ELEMENTS), no credit
  memos for returns, no intercompany flows.
- In a real system the extracts would come from CDS views / ODP extraction (e.g. via SAP Datasphere
  or SLT) instead of CSV files.
