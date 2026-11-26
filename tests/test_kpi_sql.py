"""KPI SQL on the tiny fixture: every expected value is worked out by hand in conftest.py.

Runs on SQLite always and on PostgreSQL too when TEST_DATABASE_URL is set (CI).
"""

import pytest

from src.db import render_sql
from src.dq import run_dq
from src.kpis import run_kpis
from src.load import load_staging
from src.sap_mapping import map_to_sap
from src.star_schema import build_star_schema, drop_views
from tests.conftest import olist_frames


@pytest.fixture
def kpis(engine):
    drop_views(engine)
    load_staging(engine, map_to_sap(olist_frames()))
    run_dq(engine)
    build_star_schema(engine)
    return run_kpis(engine, write_csv=False)


def test_headline_kpis(kpis):
    h = kpis["headline"].iloc[0]
    assert h.sales_orders == 4          # o5 is outside the analysis window
    assert h.order_items == 5
    assert h.net_revenue == pytest.approx(380.0)
    assert h.otif_rate == pytest.approx(2 / 4)
    assert h.in_full_rate == pytest.approx(3 / 4)
    assert h.on_time_rate == pytest.approx(2 / 3)
    assert h.cancellation_rate == pytest.approx(1 / 4)
    assert h.avg_lead_time_days == pytest.approx(28 / 3)
    assert h.avg_promised_days == pytest.approx(31 / 3)
    assert h.avg_approval_hours == pytest.approx(28 / 4)
    assert h.low_review_rate == pytest.approx(2 / 4)
    assert h.seller_handover_on_time_rate == pytest.approx(2 / 3)
    assert h.fashion_revenue_share == pytest.approx(300 / 380)


def test_otif_by_state(kpis):
    df = kpis["otif_by_state"].set_index("state")
    assert df.loc["SP", "otif_rate"] == pytest.approx(2 / 3)
    assert df.loc["AL", "otif_rate"] == pytest.approx(0.0)
    assert df.loc["AL", "macro_region"] == "Northeast"


def test_late_orders_drive_complaints(kpis):
    df = kpis["review_vs_delivery"].set_index("delivery_outcome")
    assert df.loc["late", "low_review_rate"] == pytest.approx(1.0)
    assert df.loc["on time", "low_review_rate"] == pytest.approx(0.0)


def test_payment_types(kpis):
    df = kpis["payment_types"].set_index("payment_type")
    assert df.loc["credit_card", "avg_approval_hours"] == pytest.approx(1.5)
    assert df.loc["credit_card", "avg_installments"] == pytest.approx(1.5)
    assert df.loc["boleto", "avg_approval_hours"] == pytest.approx(24.0)
    assert df.loc["credit_card", "amount_rank"] == 1


def test_top_materials_rank_within_segment(kpis):
    df = kpis["top_materials"].set_index("material_id")
    assert df.loc["p1", "segment"] == "Fashion & accessories"
    assert df.loc["p1", "rank_in_segment"] == 1 and df.loc["p1", "overall_rank"] == 1


def test_date_macros_per_dialect():
    sql = "SELECT DAYS_BETWEEN(h.erdat, d.pod_ts), HOURS_BETWEEN(a.x, b.y), DATE_KEY(h.erdat)"
    lite = render_sql(sql, "sqlite")
    assert "julianday(date(d.pod_ts)) - julianday(date(h.erdat))" in lite
    assert "strftime('%Y-%m-%d', h.erdat)" in lite
    pg = render_sql(sql, "postgresql")
    assert "CAST(d.pod_ts AS DATE) - CAST(h.erdat AS DATE)" in pg
    assert "EXTRACT(EPOCH FROM" in pg and "TO_CHAR(h.erdat, 'YYYY-MM-DD')" in pg
