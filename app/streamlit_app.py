"""RetailLens Streamlit dashboard (SYNTHETIC DATA).

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
from src.db import get_engine  # noqa: E402

BLUE, ORANGE = "#2a78d6", "#eb6834"
CATEGORY_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                   "#e87ba4", "#008300", "#6250d6", "#e34948"]

st.set_page_config(page_title="RetailLens O2C - SYNTHETIC DATA", layout="wide")


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data
def read(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, engine())


def pct(x: float) -> str:
    return f"{x:.1%}"


def bar(df, x, y, title, highlight_first=True, fmt=".1%"):
    """Horizontal bar chart; the first row (worst) is highlighted in orange."""
    colors = [ORANGE if (i == 0 and highlight_first) else BLUE for i in range(len(df))]
    fig = px.bar(df, x=x, y=y, orientation="h", title=title, text=x)
    fig.update_traces(marker_color=colors, texttemplate=f"%{{x:{fmt}}}", textposition="outside",
                      cliponaxis=False)
    fig.update_layout(yaxis={"categoryorder": "array", "categoryarray": list(df[y])[::-1]},
                      height=340, margin={"l": 10, "r": 60, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None)
    if fmt.endswith("%"):
        fig.update_xaxes(tickformat=".0%")
    return fig


# ---------------------------------------------------------------- page: overview
def page_overview():
    st.title("RetailLens - Order-to-Cash KPI Overview (SYNTHETIC DATA)")
    st.caption("Fashion wholesale, SAP S/4HANA SD structures (VBAK/VBAP, LIKP/LIPS, VBRK/VBRP). "
               "All data is synthetic, produced by a seeded generator.")
    h = read("SELECT * FROM kpi_headline").iloc[0]
    c = st.columns(3) + st.columns(3)  # two rows of three KPI tiles
    c[0].metric("Net revenue", f"EUR {h.total_revenue / 1e6:.2f}M")
    c[1].metric("OTIF (on-time in-full)", pct(h.otif_rate))
    c[2].metric("Avg order-to-delivery lead time", f"{h.avg_lead_time_days:.1f} days")
    c[3].metric("Fill rate", pct(h.fill_rate))
    c[4].metric("Return rate (units)", pct(h.return_rate))
    c[5].metric("Avg invoice-to-cash", f"{h.avg_invoice_to_cash_days:.1f} days")

    rev = read("SELECT * FROM kpi_revenue_monthly")
    fig = px.line(rev, x="month_key", y="net_revenue", title="Monthly net revenue (EUR)",
                  markers=True)
    fig.update_traces(line_color=BLUE, marker_color=BLUE)
    fig.update_layout(height=320, margin={"l": 10, "r": 10, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    otif = read("SELECT * FROM kpi_otif_by_country ORDER BY otif_rate")
    left.plotly_chart(bar(otif, "otif_rate", "country", "OTIF % by country (worst first)"),
                      use_container_width=True)
    ret = read("SELECT * FROM kpi_return_rate_by_category ORDER BY return_rate DESC")
    right.plotly_chart(bar(ret, "return_rate", "category", "Return rate % by category"),
                       use_container_width=True)


# ---------------------------------------------------------------- page: drill-down
@st.cache_data
def order_items() -> pd.DataFrame:
    return read("""
        SELECT f.*, c.country, c.region, m.category, m.season, d.month_key
        FROM ZC_SalesOrderItem f
        JOIN ZI_Customer c ON c.customer_id = f.customer_id
        JOIN ZI_Material m ON m.material_id = f.material_id
        JOIN ZI_CalendarDate d ON d.calendar_date = f.order_date
        WHERE f.delivery_count > 0""")


@st.cache_data
def billing_items() -> pd.DataFrame:
    return read("""
        SELECT b.*, c.country, c.region, m.category, m.season, m.material_name
        FROM ZC_BillingItem b
        JOIN ZI_Customer c ON c.customer_id = b.customer_id
        JOIN ZI_Material m ON m.material_id = b.material_id""")


def page_drilldown():
    st.title("Drill-down by country, category and season (SYNTHETIC DATA)")
    oi, bi = order_items(), billing_items()
    f1, f2, f3 = st.columns(3)
    countries = f1.multiselect("Country (LAND1)", sorted(oi.country.unique()))
    categories = f2.multiselect("Category (MATKL)", sorted(oi.category.unique()))
    seasons = f3.multiselect("Season (SAISO)", sorted(oi.season.unique()))

    def apply(df):
        if countries:
            df = df[df.country.isin(countries)]
        if categories:
            df = df[df.category.isin(categories)]
        if seasons:
            df = df[df.season.isin(seasons)]
        return df

    oi, bi = apply(oi), apply(bi)
    if oi.empty:
        st.warning("No data for this selection.")
        return
    c = st.columns(5)
    c[0].metric("Net revenue", f"EUR {bi.net_revenue.sum() / 1e6:.2f}M")
    c[1].metric("Order items", f"{len(oi):,}")
    c[2].metric("OTIF", pct(oi.otif_flag.mean()))
    c[3].metric("Avg lead time", f"{oi.lead_time_days.mean():.1f} days")
    c[4].metric("Return rate", pct(bi.returned_qty.sum() / bi.billed_qty.sum()))

    left, right = st.columns(2)
    by_region = (oi.groupby(["country", "region"]).otif_flag.mean().reset_index()
                 .assign(label=lambda d: d.country + "-" + d.region)
                 .sort_values("otif_flag").head(12))
    left.plotly_chart(bar(by_region, "otif_flag", "label", "Lowest OTIF regions (REGIO)"),
                      use_container_width=True)
    monthly = (oi.groupby(["month_key", "category"]).order_value.sum().reset_index())
    fig = px.bar(monthly, x="month_key", y="order_value", color="category",
                 title="Order value by month and category (EUR)",
                 color_discrete_sequence=CATEGORY_COLORS)
    fig.update_layout(height=340, margin={"l": 10, "r": 10, "t": 50, "b": 10},
                      xaxis_title=None, yaxis_title=None, legend_title=None)
    right.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 materials by net revenue in this selection")
    top = (bi.groupby(["material_id", "material_name", "category"])
           .agg(net_revenue=("net_revenue", "sum"), billed_qty=("billed_qty", "sum"),
                returned_qty=("returned_qty", "sum"))
           .reset_index().sort_values("net_revenue", ascending=False).head(10))
    top["return_rate"] = (top.returned_qty / top.billed_qty).map(pct)
    top["net_revenue"] = top.net_revenue.map("EUR {:,.0f}".format)
    st.dataframe(top, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------- page: data quality
def page_quality():
    st.title("Data quality and quarantine (SYNTHETIC DATA)")
    st.caption("Rules: mandatory fields, non-negative quantities/values, referential integrity "
               "(VBAP->VBAK, LIPS->LIKP, VBRP->VBRK, VBAK->KNA1, VBAP->MARA). Failed rows are "
               "kept in dq_quarantine with the reason - never silently dropped.")
    log = read("SELECT * FROM dq_run_log")
    latest_run = log.sort_values("run_ts").run_id.iloc[-1]  # most recent pipeline run
    last = log[log.run_id == latest_run]
    c = st.columns(4)
    c[0].metric("Rows checked", f"{last.rows_in.sum():,}")
    c[1].metric("Rows passed", f"{last.rows_passed.sum():,}")
    c[2].metric("Rows quarantined", f"{last.rows_quarantined.sum():,}")
    c[3].metric("Pipeline runs logged", f"{log.run_id.nunique():,}")

    q = read("SELECT * FROM dq_quarantine")
    left, right = st.columns([1, 1])
    by_rule = (q.groupby(["source_table", "rule", "reason"]).size()
               .reset_index(name="violations").sort_values("violations", ascending=False))
    left.subheader("Violations by rule")
    left.dataframe(by_rule, hide_index=True, use_container_width=True)
    right.subheader("Latest run log (per table)")
    right.dataframe(last[["source_table", "rows_in", "rows_passed", "rows_quarantined"]],
                    hide_index=True, use_container_width=True)

    st.subheader("Quarantined records (sample)")
    table = st.selectbox("Source table", sorted(q.source_table.unique()))
    st.dataframe(q[q.source_table == table][["source_table", "record_key", "rule", "reason",
                                             "raw_record"]].head(50),
                 hide_index=True, use_container_width=True)


PAGES = {"KPI overview": page_overview, "Drill-down": page_drilldown,
         "Data quality": page_quality}

st.sidebar.title("RetailLens")
st.sidebar.caption("SAP S/4HANA order-to-cash analytics\n\n**SYNTHETIC DATA**")
default = st.query_params.get("page", "KPI overview")
choice = st.sidebar.radio("Page", list(PAGES),
                          index=list(PAGES).index(default) if default in PAGES else 0)
PAGES[choice]()
