"""Data-quality rules on real Olist issue types: errors quarantine, warnings only log."""

import pandas as pd

from src.dq import check_table, run_dq
from src.load import load_staging
from src.sap_mapping import map_to_sap
from src.star_schema import drop_views
from tests.conftest import olist_frames

T = pd.Timestamp


def _ctx(vbak: pd.DataFrame) -> dict:
    return {"clean": {"vbak": vbak}, "raw": {}}


def test_delivered_before_goods_issue_is_quarantined():
    vbak = pd.DataFrame({"vbeln": ["A", "B"], "erdat": [T("2017-01-01")] * 2,
                         "zzstatus": ["delivered"] * 2})
    likp = pd.DataFrame({"vbeln": ["A", "B"], "kunnr": ["u", "u"],
                         "wadat_ist": [T("2017-01-03"), T("2017-01-05")],
                         "podat": [T("2017-01-04"), T("2017-01-04")]})
    kept, log = check_table(likp, "likp", _ctx(vbak))
    assert list(kept.vbeln) == ["A"]
    assert log.iloc[0].severity == "error"
    assert "PODAT before goods issue" in log.iloc[0].reason


def test_goods_issue_before_order_and_missing_pod_are_errors():
    vbak = pd.DataFrame({"vbeln": ["A", "B"], "erdat": [T("2017-01-10")] * 2,
                         "zzstatus": ["delivered", "delivered"]})
    likp = pd.DataFrame({"vbeln": ["A", "B"], "kunnr": ["u", "u"],
                         "wadat_ist": [T("2017-01-09"), T("2017-01-12")],
                         "podat": [T("2017-01-15"), None]})
    kept, log = check_table(likp, "likp", _ctx(vbak))
    assert kept.empty
    assert set(log.reason) == {"LIKP goods issue WADAT_IST before order date VBAK.ERDAT",
                               "LIKP status delivered but proof of delivery PODAT missing"}


def test_missing_category_is_a_warning_and_row_is_kept():
    mara = pd.DataFrame({"matnr": ["p1"], "matkl": [None], "brgew": [1.0], "laeng": [1.0],
                         "breit": [1.0], "hoehe": [1.0]})
    ctx = {"clean": {"t023t": pd.DataFrame({"matkl": ["x"]})}, "raw": {}}
    kept, log = check_table(mara, "mara", ctx)
    assert len(kept) == 1
    assert list(log.severity) == ["warning"]


def test_pipeline_dq_on_fixture(engine):
    """o4 has PODAT < WADAT_IST: its delivery is quarantined and its item becomes an orphan."""
    drop_views(engine)
    load_staging(engine, map_to_sap(olist_frames()))
    result = run_dq(engine)
    assert result["rows_quarantined"] == 2
    assert result["quarantine_by_table"] == {"likp": 1, "lips": 1}
    assert result["warnings"] == 2  # p3 without category, seller zip 13000 not in geolocation
