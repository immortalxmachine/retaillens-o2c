"""KPI SQL on the tiny fixture: every expected value is worked out by hand in conftest.py.

Runs on SQLite always and on PostgreSQL too when TEST_DATABASE_URL is set (CI).
"""

import pytest

from src.db import render_sql
from src.dq import run_dq
from src.kpis import run_kpis
from src.load import load_staging
from src.star_schema import build_star_schema, drop_views
from tests.conftest import tiny_tables


@pytest.fixture
def kpis(engine):
    drop_views(engine)
    load_staging(engine, tiny_tables())
    run_dq(engine)
    build_star_schema(engine, start="2023-12-01", end="2024-03-31")
    return run_kpis(engine, write_csv=False)


def test_headline_kpis(kpis):
    h = kpis["headline"].iloc[0]
    assert h.sales_orders == 2
    assert h.order_items == 3
    assert h.total_revenue == pytest.approx(170.0)
    assert h.otif_rate == pytest.approx(1 / 3)
    assert h.on_time_rate == pytest.approx(2 / 3)
    assert h.in_full_rate == pytest.approx(2 / 3)
    assert h.avg_lead_time_days == pytest.approx(14 / 3)
    assert h.fill_rate == pytest.approx(17 / 19)
    assert h.return_rate == pytest.approx(2 / 17)
    assert h.avg_invoice_to_cash_days == pytest.approx(30)
    assert h.open_receivables_share == pytest.approx(40 / 170)


def test_otif_by_country_ranks_worst_first(kpis):
    df = kpis["otif_by_country"]
    assert list(df.country) == ["IT", "DE"]
    assert list(df.worst_otif_rank) == [1, 2]
    assert df.otif_rate.tolist() == pytest.approx([0.0, 0.5])


def test_return_rate_by_category_uses_rank(kpis):
    df = kpis["return_rate_by_category"]
    top = df.iloc[0]
    assert top.category == "DRESSES" and top.return_rank == 1
    assert top.return_rate == pytest.approx(2 / 14)


def test_top_materials_rank_within_category(kpis):
    df = kpis["top_materials"].set_index("material_id")
    assert df.loc["M1", "rank_in_category"] == 1
    assert df.loc["M1", "overall_rank"] == 1  # 140 EUR beats M2's 30 EUR
    assert df.loc["M2", "overall_rank"] == 2


def test_days_between_macro_per_dialect():
    sql = "SELECT DAYS_BETWEEN(h.erdat, d.last_gi_date) FROM t"
    assert "julianday(d.last_gi_date) - julianday(h.erdat)" in render_sql(sql, "sqlite")
    assert "CAST(d.last_gi_date AS DATE) - CAST(h.erdat AS DATE)" in render_sql(sql, "postgresql")
