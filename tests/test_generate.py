"""Generator: same seed -> same data, SAP structure present, DQ issues injected as documented."""

import pandas as pd

from src.generate import DQ_INJECTION, generate


def test_same_seed_gives_identical_data():
    a = generate(seed=7, scale=0.05)
    b = generate(seed=7, scale=0.05)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_different_seed_gives_different_data():
    a = generate(seed=7, scale=0.05)
    b = generate(seed=8, scale=0.05)
    assert not a["vbap"].equals(b["vbap"])


def test_sap_tables_and_fields_exist():
    t = generate(seed=7, scale=0.05)
    assert {"VBELN", "ERDAT", "VDATU", "KUNNR", "NETWR", "WAERK"} <= set(t["vbak"].columns)
    assert {"VBELN", "POSNR", "MATNR", "KWMENG", "NETWR"} <= set(t["vbap"].columns)
    assert {"VBELN", "WADAT_IST"} <= set(t["likp"].columns)
    assert {"VBELN", "LFIMG", "VGBEL", "VGPOS"} <= set(t["lips"].columns)
    assert {"VBELN", "FKDAT", "NETWR"} <= set(t["vbrk"].columns)
    assert {"VBELN", "AUGDT"} <= set(t["bsad"].columns)


def test_documented_dq_issues_are_injected():
    t = generate(seed=7, scale=0.05)
    assert t["vbak"]["ERDAT"].isna().sum() == DQ_INJECTION["vbak_missing_erdat"]
    assert (t["vbap"]["KWMENG"] < 0).sum() == DQ_INJECTION["vbap_negative_kwmeng"]
    assert (~t["vbap"]["VBELN"].isin(t["vbak"]["VBELN"])).sum() == \
        DQ_INJECTION["vbap_orphan_items"]
    assert t["likp"]["WADAT_IST"].isna().sum() == DQ_INJECTION["likp_missing_wadat_ist"]
    assert (~t["lips"]["VBELN"].isin(t["likp"]["VBELN"])).sum() == \
        DQ_INJECTION["lips_orphan_items"]
