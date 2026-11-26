"""Olist -> SAP mapping: keys, documents and dates land in the right SAP fields."""

import filecmp

import pandas as pd

from src.config import SAMPLE_DIR
from src.download import OLIST_FILES
from src.make_sample import build_sample
from src.sap_mapping import map_to_sap, read_olist
from tests.conftest import olist_frames


def test_kna1_is_one_row_per_real_customer():
    t = map_to_sap(olist_frames())
    assert sorted(t["kna1"].KUNNR) == ["u1", "u2"]  # customer_unique_id, not customer_id
    assert set(t["kna1"].LAND1) == {"BR"}
    assert t["vbak"].set_index("VBELN").KUNNR.to_dict() == {
        "o1": "u1", "o2": "u2", "o3": "u1", "o4": "u1", "o5": "u2"}


def test_order_dates_map_to_sap_fields():
    t = map_to_sap(olist_frames())
    vbak = t["vbak"].set_index("VBELN")
    assert vbak.loc["o1", "VDATU"] == pd.Timestamp("2017-03-10")  # estimated delivery date
    assert vbak.loc["o1", "NETWR"] == 150.0                       # sum of item prices
    likp = t["likp"].set_index("VBELN")
    assert "o3" not in likp.index                                 # cancelled, never shipped
    assert likp.loc["o1", "WADAT_IST"] == pd.Timestamp("2017-03-03 09:00")  # carrier hand-off
    assert likp.loc["o1", "PODAT"] == pd.Timestamp("2017-03-06 15:00")      # delivered
    bsad = t["bsad"].set_index("VBELN")
    assert bsad.loc["o2", "AUGDT"] == pd.Timestamp("2017-03-03 08:00")      # payment approval
    assert bsad.loc["o2", "ZLSCH"] == "boleto"


def test_category_texts_go_to_t023t_not_invented():
    t = map_to_sap(olist_frames())
    mara = t["mara"].set_index("MATNR")
    assert mara.loc["p1", "MATKL"] == "fashion_calcados"
    assert pd.isna(mara.loc["p3", "MATKL"])                       # missing stays missing
    assert dict(zip(t["t023t"].MATKL, t["t023t"].WGBEZ, strict=True))["fashion_calcados"] \
        == "fashion_shoes"


def test_committed_sample_is_consistent_and_reproducible(tmp_path):
    olist = read_olist(SAMPLE_DIR)
    assert olist["order_items"].order_id.isin(olist["orders"].order_id).all()
    assert olist["orders"].customer_id.isin(olist["customers"].customer_id).all()
    assert olist["order_items"].product_id.isin(olist["products"].product_id).all()
    # sampling the sample again gives byte-identical files -> the sampler is deterministic
    build_sample(SAMPLE_DIR, tmp_path)
    for file in OLIST_FILES.values():
        assert filecmp.cmp(SAMPLE_DIR / file, tmp_path / file, shallow=False), file
