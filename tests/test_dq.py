"""Data-quality rules: each rule catches its case, the reason is recorded, clean rows pass."""

import pandas as pd

from src.dq import check_table, run_dq
from src.load import load_staging
from src.star_schema import drop_views
from tests.conftest import tiny_tables


def test_mandatory_rule_flags_missing_date():
    vbak = pd.DataFrame({"vbeln": ["O1", "O2"], "erdat": [pd.Timestamp("2024-01-01"), None],
                         "vdatu": [pd.Timestamp("2024-01-05")] * 2, "kunnr": ["C1", "C1"]})
    clean = {"kna1": pd.DataFrame({"kunnr": ["C1"]})}
    passed, q = check_table(vbak, "vbak", clean)
    assert list(passed.vbeln) == ["O1"]
    assert q.iloc[0].record_key == "O2"
    assert q.iloc[0].rule == "mandatory"
    assert "ERDAT is missing" in q.iloc[0].reason


def test_negative_quantity_and_orphan_item():
    vbap = pd.DataFrame({"vbeln": ["O1", "O1", "X9"], "posnr": [10, 20, 10],
                         "matnr": ["M1", "M1", "M1"], "kwmeng": [5, -3, 2],
                         "netwr": [50.0, 30.0, 20.0]})
    clean = {"vbak": pd.DataFrame({"vbeln": ["O1"]}), "mara": pd.DataFrame({"matnr": ["M1"]})}
    passed, q = check_table(vbap, "vbap", clean)
    assert len(passed) == 1
    rules = dict(zip(q.record_key, q.rule, strict=True))
    assert rules == {"O1|20": "non_negative", "X9|10": "reference"}


def test_item_of_quarantined_header_is_quarantined_too(engine):
    """Parents are cleaned first, so LIPS rows of a bad LIKP become orphans."""
    t = tiny_tables()
    t["likp"].loc[1, "WADAT_IST"] = None  # break delivery D2
    drop_views(engine)
    load_staging(engine, t)
    result = run_dq(engine)
    assert result["violations_by_rule"] == {"likp.mandatory": 1, "lips.reference": 1}
    assert result["rows_quarantined"] == 2


def test_clean_fixture_passes_everything(engine):
    drop_views(engine)
    load_staging(engine, tiny_tables())
    result = run_dq(engine)
    assert result["rows_quarantined"] == 0
    assert result["rows_passed"] == result["rows_in"]
