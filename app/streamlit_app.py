"""RetailLens Streamlit dashboard - case study on real Olist orders mapped to SAP SD.

Reads the star-schema views and kpi_* tables that `python -m src.pipeline` writes, so the
dashboard shows exactly the numbers of the SQL KPIs.

Run:  streamlit run app/streamlit_app.py --server.port 8530
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))  # make `src` importable
from src.config import ANALYSIS_END, ANALYSIS_START  # noqa: E402
from src.db import get_engine  # noqa: E402

BLUE, ORANGE = "#2a78d6", "#eb6834"
SOURCE = ("Source: Olist Brazilian E-Commerce Public Dataset (Kaggle, CC BY-NC-SA 4.0, "
          "non-commercial) - real anonymised orders mapped to SAP S/4HANA SD tables.")

st.set_page_config(page_title="RetailLens O2C case study", layout="wide")


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data
def read(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, engine())


def pct(x: float) -> str:
    return f"{x:.1%}"


def bar(df, x, y, title, fmt=".1%"):
    """Horizontal bar chart; the first row (worst) is highlighted in orange."""
    colors = [ORANGE if i == 0 else BLUE for i in range(len(df))]
    fig = px.bar(df, x=x, y=y, orientation="h", title=title, text=x)
    fig.update_traces(marker_color=colors, texttemplate=f"%{{x:{fmt}}}", textposition="outside",
                      cliponaxis=False)
    fig.update_layout(yaxis={"categoryorder": "array", "categoryarray": list(df[y])[::-1]},
                      height=360, margin={"l": 10, "r": 60, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None)
    if fmt.endswith("%"):
        fig.update_xaxes(tickformat=".0%")
    return fig


# ---------------------------------------------------------------- page: overview
def page_overview():
    st.title("RetailLens - Order-to-Cash KPI Overview (case study)")
    st.caption(f"{SOURCE} Orders placed {ANALYSIS_START} to {ANALYSIS_END}.")
    h = read("SELECT * FROM kpi_headline").iloc[0]
    c = st.columns(3) + st.columns(3)  # two rows of three KPI tiles
    c[0].metric("Net revenue (non-cancelled)", f"BRL {h.net_revenue / 1e6:.2f}M")
    c[1].metric("OTIF (on-time in-full)", pct(h.otif_rate))
    c[2].metric("Avg order-to-delivery lead time",
                f"{h.avg_lead_time_days:.1f} days", f"promised {h.avg_promised_days:.1f} days",
                delta_color="off")
    c[3].metric("Cancellation rate", f"{h.cancellation_rate:.2%}")
    c[4].metric("Complaint rate (review 1-2)", pct(h.low_review_rate))
    c[5].metric("Purchase -> payment approval", f"{h.avg_approval_hours:.1f} hours")

    rev = read("SELECT * FROM kpi_revenue_monthly")
    fig = px.line(rev, x="month_key", y="net_revenue", title="Monthly net revenue (BRL)",
                  markers=True)
    fig.update_traces(line_color=BLUE, marker_color=BLUE)
    fig.update_layout(height=320, margin={"l": 10, "r": 10, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    otif = read("SELECT * FROM kpi_otif_by_state WHERE worst_otif_rank IS NOT NULL "
                "ORDER BY otif_rate LIMIT 10")
    left.plotly_chart(bar(otif, "otif_rate", "state", "OTIF % - 10 worst states"),
                      use_container_width=True)
    cat = read("SELECT * FROM kpi_category_service WHERE complaint_rank IS NOT NULL "
               "ORDER BY complaint_rank LIMIT 10")
    right.plotly_chart(bar(cat, "low_review_rate", "category",
                           "Complaint rate - top 10 categories"), use_container_width=True)


# ---------------------------------------------------------------- page: drill-down
@st.cache_data
def order_items() -> pd.DataFrame:
    return read(f"""
        SELECT f.order_id, f.item_value, f.freight_value, f.otif_eligible, f.otif_flag,
               f.in_full_flag, f.cancelled_flag, f.lead_time_days, f.transit_days,
               f.has_review, f.low_review_flag, f.material_id,
               c.state, c.macro_region, m.category, m.segment, d.month_key
        FROM ZC_SalesOrderItem f
        JOIN ZI_Customer c ON c.customer_id = f.customer_id
        JOIN ZI_Material m ON m.material_id = f.material_id
        JOIN ZI_CalendarDate d ON d.date_key = f.order_date_key
        WHERE d.date_key BETWEEN '{ANALYSIS_START}' AND '{ANALYSIS_END}'""")


def page_drilldown():
    st.title("Drill-down by region, segment and category (case study)")
    st.caption(SOURCE)
    oi = order_items()
    f1, f2, f3 = st.columns(3)
    regions = f1.multiselect("Macro-region (from KNA1.REGIO)",
                             sorted(oi.macro_region.unique()))
    segments = f2.multiselect("Segment", sorted(oi.segment.unique()))
    categories = f3.multiselect("Category (MATKL)", sorted(oi.category.unique()))
    if regions:
        oi = oi[oi.macro_region.isin(regions)]
    if segments:
        oi = oi[oi.segment.isin(segments)]
    if categories:
        oi = oi[oi.category.isin(categories)]
    if oi.empty:
        st.warning("No data for this selection.")
        return

    # rates only count where they are defined: OTIF for eligible items, complaints for reviews
    oi = oi.assign(otif_flag=oi.otif_flag.where(oi.otif_eligible == 1),
                   low_review_flag=oi.low_review_flag.where(oi.has_review == 1))
    elig = oi[oi.otif_eligible == 1]
    delivered = oi[oi.in_full_flag == 1]
    reviewed = oi[oi.has_review == 1].drop_duplicates("order_id")
    c = st.columns(5)
    c[0].metric("Net revenue", f"BRL {oi[oi.cancelled_flag == 0].item_value.sum() / 1e6:.2f}M")
    c[1].metric("Order items", f"{len(oi):,}")
    c[2].metric("OTIF", pct(elig.otif_flag.mean()))
    c[3].metric("Avg lead time", f"{delivered.lead_time_days.mean():.1f} days")
    c[4].metric("Complaint rate", pct(reviewed.low_review_flag.mean()))

    left, right = st.columns(2)
    by_state = (elig.groupby("state").agg(otif=("otif_flag", "mean"), n=("otif_flag", "size"))
                .reset_index().query("n >= 30").sort_values("otif").head(10))
    left.plotly_chart(bar(by_state, "otif", "state", "Lowest OTIF states (min. 30 items)"),
                      use_container_width=True)
    monthly = (oi[oi.cancelled_flag == 0].groupby(["month_key", "segment"]).item_value.sum()
               .reset_index())
    fig = px.bar(monthly, x="month_key", y="item_value", color="segment",
                 title="Net revenue by month and segment (BRL)",
                 color_discrete_map={"Fashion & accessories": ORANGE, "Other": BLUE})
    fig.update_layout(height=360, margin={"l": 10, "r": 10, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None, legend_title=None)
    right.plotly_chart(fig, use_container_width=True)

    st.subheader("Categories in this selection")
    cats = (oi.groupby(["segment", "category"])
            .agg(order_items=("order_id", "size"), net_revenue=("item_value", "sum"),
                 otif=("otif_flag", "mean"), cancelled=("cancelled_flag", "mean"),
                 complaints=("low_review_flag", "mean"),
                 avg_lead_days=("lead_time_days", "mean"))
            .reset_index().sort_values("net_revenue", ascending=False).head(12))
    for col in ("otif", "cancelled", "complaints"):
        cats[col] = cats[col].map(pct)
    cats["net_revenue"] = cats.net_revenue.map("BRL {:,.0f}".format)
    cats["avg_lead_days"] = cats.avg_lead_days.round(1)
    st.dataframe(cats, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------- page: data quality
def page_quality():
    st.title("Data quality and quarantine (real Olist issues)")
    st.caption("Errors are quarantined (row not loaded to cln_*); warnings are logged but the "
               "row is kept. Rules: mandatory fields, non-negative values, references "
               "(VBAP->VBAK, LIPS->LIKP, BSAD->VBAK, ...) and consistency checks "
               "(e.g. delivered before it was shipped).")
    log = read("SELECT * FROM dq_run_log")
    latest_run = log.sort_values("run_ts").run_id.iloc[-1]  # most recent pipeline run
    last = log[log.run_id == latest_run]
    c = st.columns(4)
    c[0].metric("Rows checked", f"{last.rows_in.sum():,}")
    c[1].metric("Rows quarantined (errors)", f"{last.rows_quarantined.sum():,}")
    c[2].metric("Warnings logged", f"{last.warnings.sum():,}")
    c[3].metric("Pipeline runs logged", f"{log.run_id.nunique():,}")

    q = read("SELECT * FROM dq_quarantine")
    left, right = st.columns([3, 2])
    by_rule = (q.groupby(["severity", "source_table", "reason"]).size()
               .reset_index(name="rows").sort_values("rows", ascending=False))
    left.subheader("Issues by rule")
    left.dataframe(by_rule, hide_index=True, use_container_width=True)
    right.subheader("Latest run log (per SAP table)")
    right.dataframe(last[["source_table", "rows_in", "rows_passed", "rows_quarantined",
                          "warnings"]], hide_index=True, use_container_width=True)

    st.subheader("Logged records (raw JSON kept for re-processing)")
    reason = st.selectbox("Rule", list(by_rule.reason))
    st.dataframe(q[q.reason == reason][["severity", "source_table", "record_key",
                                        "raw_record"]].head(50),
                 hide_index=True, use_container_width=True)


PAGES = {"KPI overview": page_overview, "Drill-down": page_drilldown,
         "Data quality": page_quality}

st.sidebar.title("RetailLens")
st.sidebar.caption("SAP S/4HANA order-to-cash case study\n\n"
                   "Real data: Olist (Kaggle), CC BY-NC-SA 4.0")
default = st.query_params.get("page", "KPI overview")
choice = st.sidebar.radio("Page", list(PAGES),
                          index=list(PAGES).index(default) if default in PAGES else 0)
PAGES[choice]()
