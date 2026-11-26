"""RetailLens end-to-end pipeline - case study on real Olist data mapped to SAP SD structures.

    download -> map to SAP tables -> load staging -> data quality -> star schema -> KPIs
             -> Power BI export -> charts -> metrics.json -> insights -> README/resume numbers

Run:  python -m src.pipeline            (SQLite by default, PostgreSQL if DATABASE_URL is set)
      RETAILLENS_RAW_DIR=data/sample python -m src.pipeline   (committed sample, used in CI)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import pandas as pd

from src.charts import make_charts
from src.config import ANALYSIS_END, ANALYSIS_START, METRICS_PATH, RAW_DIR, ROOT, SOURCE_NOTICE
from src.db import get_engine
from src.download import download, is_present
from src.dq import run_dq
from src.export_powerbi import export_star_schema
from src.insights import write_insights
from src.kpis import run_kpis
from src.load import load_staging
from src.render_docs import render
from src.sap_mapping import map_to_sap, read_olist
from src.star_schema import STAR_VIEWS, build_star_schema, drop_views


def log(step: str, msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {step:<12} {msg}", flush=True)


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-friendly list of dicts with floats rounded to 4 decimals."""
    return json.loads(df.round(4).to_json(orient="records"))


def year_over_year(rev: pd.DataFrame) -> dict:
    """Compare the same months of the last two years (the data ends in August)."""
    rev = rev.assign(year=rev.month_key.str[:4], month=rev.month_key.str[5:])
    last = rev.year.max()
    prev = str(int(last) - 1)
    months = set(rev[rev.year == last].month) & set(rev[rev.year == prev].month)
    cur = rev[(rev.year == last) & rev.month.isin(months)].net_revenue.sum()
    old = rev[(rev.year == prev) & rev.month.isin(months)].net_revenue.sum()
    span = f"{min(months)}-{max(months)}" if months else "n/a"
    return {"label": f"{last} vs {prev} (months {span})",
            "growth": round(float(cur / old - 1), 4) if old else None}


def build_metrics(engine, source_counts, sap_counts, dq, star_counts, kpis) -> dict:
    h = kpis["headline"].iloc[0]
    counts = ("sales_orders", "order_items", "customers", "sellers")
    return {
        "source": SOURCE_NOTICE,
        "dataset": "full Kaggle download" if RAW_DIR == ROOT / "data" / "raw"
        else f"sample in {RAW_DIR.relative_to(ROOT).as_posix()}",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "database": engine.dialect.name,
        "analysis_window": {"start": ANALYSIS_START, "end": ANALYSIS_END},
        "source_row_counts": source_counts,
        "sap_row_counts": sap_counts,
        "dq": dq,
        "star_schema_row_counts": star_counts,
        # counts are integers, everything else is a rate / amount rounded to 4 decimals
        "headline": {k: (int(v) if k in counts else round(float(v), 4)) for k, v in h.items()},
        "yoy": year_over_year(kpis["revenue_monthly"]),
        "kpis": {name: _records(df) for name, df in kpis.items()
                 if name not in ("headline", "revenue_by_region_segment_category",
                                 "otif_monthly", "revenue_monthly")},
    }


def main() -> dict:
    t0 = time.time()
    engine = get_engine()
    log("start", f"RetailLens pipeline - real Olist data - database: {engine.dialect.name}")

    if not is_present(RAW_DIR):
        download(RAW_DIR)
    olist = read_olist(RAW_DIR)
    source_counts = {name: len(df) for name, df in olist.items()}
    log("source", f"{RAW_DIR.relative_to(ROOT).as_posix()}: "
                  + ", ".join(f"{k}={v:,}" for k, v in source_counts.items()))

    tables = map_to_sap(olist)
    sap_counts = {name: len(df) for name, df in tables.items()}
    log("map", "SAP tables: " + ", ".join(f"{k.upper()}={v:,}" for k, v in sap_counts.items()))

    drop_views(engine)  # views depend on tables; drop them before replacing tables
    load_staging(engine, tables)
    log("load", f"{sum(sap_counts.values()):,} rows loaded into {len(sap_counts)} stg_* tables")

    dq = run_dq(engine)
    log("dq", f"run {dq['run_id']}: {dq['rows_in']:,} rows checked, {dq['rows_passed']:,} "
              f"kept, {dq['rows_quarantined']:,} quarantined, {dq['warnings']:,} warnings")
    for reason, n in dq["issues_by_reason"].items():
        log("dq", f"  {n:>6,}  {reason}")

    build_star_schema(engine)
    star_counts = {logical: int(pd.read_sql(f"SELECT COUNT(*) AS n FROM {view}", engine).n[0])
                   for logical, view in STAR_VIEWS.items()}
    log("star", ", ".join(f"{k}={v:,}" for k, v in star_counts.items()))

    kpis = run_kpis(engine)
    h = kpis["headline"].iloc[0]
    log("kpi", f"{len(kpis)} KPI queries -> kpi_* tables and reports/kpi/*.csv")
    log("kpi", f"revenue BRL {h.net_revenue:,.0f} | OTIF {h.otif_rate:.1%} | lead time "
               f"{h.avg_lead_time_days:.1f} d | cancelled {h.cancellation_rate:.2%} | "
               f"complaints {h.low_review_rate:.1%} | approval {h.avg_approval_hours:.1f} h")

    exported = export_star_schema(engine)
    log("powerbi", f"exported {len(exported)} tables to powerbi/data (CSV + Parquet)")

    charts = make_charts(kpis)
    log("charts", f"{len(charts)} PNG charts -> reports/charts/")

    metrics = build_metrics(engine, source_counts, sap_counts, dq, star_counts, kpis)
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
