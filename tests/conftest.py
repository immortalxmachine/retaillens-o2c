"""Shared fixtures: a tiny hand-made SAP dataset whose KPI answers are known in advance.

    O1 (customer C1, DE): item 10 = 10 x M1 (dress), item 20 = 5 x M2 (top)
    O2 (customer C2, IT): item 10 = 4 x M1
    requested delivery date (VDATU) for both: 2024-01-06

    D1 ships O1 on 2024-01-04 (on time) - item 20 only 3 of 5 (short -> not in full)
    D2 ships O2 on 2024-01-09 (3 days late)
    B1 bills D1 (EUR 130), paid 30 days later. B2 bills D2 (EUR 40), still open.
    R1 returns 2 dresses against B1 item 10.

Expected: OTIF 1/3, on-time 2/3, in-full 2/3, lead time (3+3+8)/3, fill rate 17/19,
          revenue 170, return rate 2/17, invoice-to-cash 30 days, open share 40/170.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

from src.db import get_engine

D = pd.Timestamp


def tiny_tables() -> dict[str, pd.DataFrame]:
    return {
        "kna1": pd.DataFrame({"KUNNR": ["C1", "C2"], "NAME1": ["Alpha GmbH", "Beta S.r.l."],
                              "LAND1": ["DE", "IT"], "REGIO": ["BY", "LOM"]}),
        "mara": pd.DataFrame({"MATNR": ["M1", "M2"], "MATKL": ["DRESSES", "TOPS"],
                              "SAISO": ["SS", "AW"], "MTART": ["FERT", "FERT"]}),
        "makt": pd.DataFrame({"MATNR": ["M1", "M2"], "MAKTX": ["Midi Dress", "T-Shirt"],
                              "SPRAS": ["E", "E"]}),
        "vbak": pd.DataFrame({"VBELN": ["O1", "O2"], "AUART": ["OR", "OR"],
                              "ERDAT": [D("2024-01-01")] * 2, "VDATU": [D("2024-01-06")] * 2,
                              "KUNNR": ["C1", "C2"], "VKORG": ["1000"] * 2,
                              "NETWR": [150.0, 40.0], "WAERK": ["EUR"] * 2}),
        "vbap": pd.DataFrame({"VBELN": ["O1", "O1", "O2"], "POSNR": [10, 20, 10],
                              "MATNR": ["M1", "M2", "M1"], "KWMENG": [10, 5, 4],
                              "VRKME": ["PC"] * 3, "NETWR": [100.0, 50.0, 40.0],
                              "WAERK": ["EUR"] * 3}),
        "likp": pd.DataFrame({"VBELN": ["D1", "D2"], "ERDAT": [D("2024-01-03"), D("2024-01-08")],
                              "KUNNR": ["C1", "C2"], "LFDAT": [D("2024-01-06")] * 2,
                              "WADAT_IST": [D("2024-01-04"), D("2024-01-09")]}),
        "lips": pd.DataFrame({"VBELN": ["D1", "D1", "D2"], "POSNR": [10, 20, 10],
                              "MATNR": ["M1", "M2", "M1"], "LFIMG": [10, 3, 4],
                              "VGBEL": ["O1", "O1", "O2"], "VGPOS": [10, 20, 10]}),
        "vbrk": pd.DataFrame({"VBELN": ["B1", "B2"], "FKART": ["F2", "F2"],
                              "FKDAT": [D("2024-01-04"), D("2024-01-09")],
                              "KUNAG": ["C1", "C2"], "NETWR": [130.0, 40.0],
                              "WAERK": ["EUR"] * 2}),
        "vbrp": pd.DataFrame({"VBELN": ["B1", "B1", "B2"], "POSNR": [10, 20, 10],
                              "MATNR": ["M1", "M2", "M1"], "FKIMG": [10, 3, 4],
                              "NETWR": [100.0, 30.0, 40.0], "VGBEL": ["D1", "D1", "D2"],
                              "VGPOS": [10, 20, 10], "AUBEL": ["O1", "O1", "O2"],
                              "AUPOS": [10, 20, 10]}),
        "bsad": pd.DataFrame({"BELNR": ["P1"], "KUNNR": ["C1"], "VBELN": ["B1"],
                              "AUGDT": [D("2024-02-03")], "DMBTR": [130.0], "WAERS": ["EUR"]}),
        "returns": pd.DataFrame({"VBELN": ["R1"], "POSNR": [10], "AUART": ["RE"],
                                 "ERDAT": [D("2024-01-20")], "KUNNR": ["C1"], "MATNR": ["M1"],
                                 "KWMENG": [2], "NETWR": [20.0], "AUGRU": ["R01"],
                                 "VGBEL": ["B1"], "VGPOS": [10]}),
    }


def _engine_params():
    params = ["sqlite"]
    if os.getenv("TEST_DATABASE_URL"):  # set in CI -> the same tests also run on PostgreSQL
        params.append("postgresql")
    return params


@pytest.fixture(params=_engine_params())
def engine(request, tmp_path):
    if request.param == "sqlite":
        eng = get_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    else:
        eng = get_engine(os.environ["TEST_DATABASE_URL"])
    yield eng
    eng.dispose()
