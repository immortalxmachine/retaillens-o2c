"""Stage 3 - build the star schema as SQL views (sql/0*.sql, CDS-style names).

    dim_customer    = ZI_Customer         fact_order_item = ZC_SalesOrderItem
    dim_seller      = ZI_Seller           fact_delivery   = ZC_DeliveryItem
    dim_material    = ZI_Material         fact_payment    = ZC_Payment
    dim_date        = ZI_CalendarDate

ZI_ = interface (reusable) view, ZC_ = consumption view - the naming convention SAP uses for
CDS views in S/4HANA (customer objects start with Z).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import ANALYSIS_END, ANALYSIS_START, SQL_DIR
from src.db import run_statements, write_table

# Logical star-schema name -> view name (used for Power BI export and docs)
STAR_VIEWS = {
    "dim_customer": "ZI_Customer",
    "dim_seller": "ZI_Seller",
    "dim_material": "ZI_Material",
    "dim_date": "ZI_CalendarDate",
    "fact_order_item": "ZC_SalesOrderItem",
    "fact_delivery": "ZC_DeliveryItem",
    "fact_payment": "ZC_Payment",
}


def view_files() -> list:
    """The view scripts in execution order (01_, 02_, ...)."""
    return sorted(SQL_DIR.glob("0*.sql"))


def drop_views(engine: Engine) -> None:
    """Drop views first so the tables underneath can be replaced (PostgreSQL enforces this)."""
    cascade = " CASCADE" if engine.dialect.name == "postgresql" else ""
    with engine.begin() as conn:
        for name in reversed(list(STAR_VIEWS.values())):
            conn.execute(text(f"DROP VIEW IF EXISTS {name}{cascade}"))


def build_calendar(start: str, end: str) -> pd.DataFrame:
    """Calendar dimension: one row per day with the attributes reports slice by."""
    d = pd.DataFrame({"calendar_date": pd.date_range(start, end, freq="D")})
    dt = d["calendar_date"].dt
    d.insert(0, "date_key", dt.strftime("%Y-%m-%d"))
    d["year_num"] = dt.year
    d["quarter_num"] = dt.quarter
    d["month_num"] = dt.month
    d["month_key"] = dt.strftime("%Y-%m")
    d["weekday_num"] = dt.day_of_week
    d["is_weekend"] = (dt.day_of_week >= 5).astype(int)
    d["is_festive"] = (
        ((d["month_num"] == 11) & (dt.day >= 10)) | (d["month_num"] == 12)
    ).astype(int)
    d["in_analysis_window"] = d["calendar_date"].between(
        pd.Timestamp(ANALYSIS_START), pd.Timestamp(ANALYSIS_END)).astype(int)
    return d


def build_star_schema(engine: Engine, start: str = "2016-09-01", end: str = "2018-12-31") -> list:
    """Create ref_calendar and all views. Returns the list of views created."""
    write_table(engine, build_calendar(start, end), "ref_calendar")
    for path in view_files():
        run_statements(engine, path.read_text(encoding="utf-8"))
    return list(STAR_VIEWS.values())
