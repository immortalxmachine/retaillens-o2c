"""RetailLens end-to-end pipeline (SYNTHETIC DATA).

    generate -> load staging -> data quality -> star schema -> KPIs
             -> Power BI export -> charts -> insights -> metrics.json -> README/resume numbers

Run:  python -m src.pipeline            (SQLite by default, PostgreSQL if DATABASE_URL is set)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import pandas as pd

from src.charts import make_charts
from src.config import METRICS_PATH, SEED
from src.db import get_engine
from src.dq import run_dq
from src.export_powerbi import export_star_schema
from src.generate import DQ_INJECTION, generate, write_csv
from src.insights import write_insights
from src.kpis import run_kpis
from src.load import load_staging
from src.render_docs import render
from src.star_schema import STAR_VIEWS, build_star_schema, drop_views


def log(step: str, msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {step:<12} {msg}", flush=True)


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-friendly list of dicts with floats rounded to 4 decimals."""
    return json.loads(df.round(4).to_json(orient="records"))


def build_metrics(engine, raw_counts, dq, star_counts, kpis) -> dict:
    h = kpis["headline"].iloc[0]
    rev = kpis["revenue_monthly"].assign(year=lambda d: d.month_key.str[:4])
    by_year = rev.groupby("year").net_revenue.sum()
    years = sorted(by_year.index)
    orders = pd.read_sql("SELECT MIN(order_date) AS a, MAX(order_date) AS b "
                         "FROM ZC_SalesOrderItem", engine).iloc[0]
    return {
        "data_label": "SYNTHETIC DATA - seeded generator, SAP S/4HANA SD table structures",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED,
        "database": engine.dialect.name,
        "date_range": {"first_order": str(orders.a)[:10], "last_order": str(orders.b)[:10]},
        "raw_row_counts": raw_counts,
        "dq_injected": DQ_INJECTION,
        "dq": dq,
        "star_schema_row_counts": star_counts,
        # counts are integers, everything else is a rate / amount rounded to 4 decimals
        "headline": {k: (int(v) if k in ("sales_orders", "order_items") else round(float(v), 4))
                     for k, v in h.items()},
        "revenue_by_year": {y: round(float(by_year[y]), 2) for y in years},
        "yoy_revenue_growth": round(float(by_year[years[-1]] / by_year[years[-2]] - 1), 4),
        "kpis": {name: _records(df) for name, df in kpis.items()
                 if name not in ("headline", "revenue_by_region_season_category",
                                 "otif_monthly", "revenue_monthly")},
    }


def main() -> dict:
    t0 = time.time()
    engine = get_engine()
    log("start", f"RetailLens pipeline - SYNTHETIC DATA - database: {engine.dialect.name}")

    tables = generate(SEED)
    write_csv(tables)
    raw_counts = {name: len(df) for name, df in tables.items()}
    log("generate", f"seed={SEED}: " + ", ".join(f"{k}={v:,}" for k, v in raw_counts.items()))

    drop_views(engine)  # views depend on tables; drop them before replacing tables
    load_staging(engine, tables)
    log("load", f"{sum(raw_counts.values()):,} rows loaded into {len(raw_counts)} stg_* tables")

    dq = run_dq(engine)
    log("dq", f"run {dq['run_id']}: {dq['rows_in']:,} rows checked, "
              f"{dq['rows_passed']:,} passed, {dq['rows_quarantined']:,} quarantined")
    for rule, n in dq["violations_by_rule"].items():
        log("dq", f"  {rule:<22} {n:>4} violations")

    build_star_schema(engine)
    star_counts = {logical: int(pd.read_sql(f"SELECT COUNT(*) AS n FROM {view}", engine).n[0])
                   for logical, view in STAR_VIEWS.items()}
    log("star", ", ".join(f"{k}={v:,}" for k, v in star_counts.items()))

    kpis = run_kpis(engine)
    h = kpis["headline"].iloc[0]
    log("kpi", f"{len(kpis)} KPI queries -> kpi_* tables and reports/kpi/*.csv")
    log("kpi", f"revenue EUR {h.total_revenue:,.0f} | OTIF {h.otif_rate:.1%} | lead time "
               f"{h.avg_lead_time_days:.1f} d | fill {h.fill_rate:.1%} | returns "
               f"{h.return_rate:.1%} | invoice-to-cash {h.avg_invoice_to_cash_days:.1f} d")

    exported = export_star_schema(engine)
    log("powerbi", f"exported {len(exported)} tables to powerbi/data (CSV + Parquet)")

    charts = make_charts(kpis)
    log("charts", f"{len(charts)} PNG charts -> reports/charts/")

    metrics = build_metrics(engine, raw_counts, dq, star_counts, kpis)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log("metrics", "metrics.json written")

    write_insights(kpis, metrics)
    log("insights", "reports/insights.md written (5 findings)")

    render(metrics)
    log("docs", "README metrics table and RESUME_BULLETS.md rendered from metrics.json")
    log("done", f"pipeline finished in {time.time() - t0:.1f}s")
    return metrics


if __name__ == "__main__":
    main()
