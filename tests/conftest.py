"""Shared fixtures: a tiny hand-made dataset in the ORIGINAL Olist CSV layout.

It goes through the real code path (map_to_sap -> load -> DQ -> views -> KPI SQL), and every
expected KPI value below is worked out by hand:

    o1 (customer u1, SP) delivered on time : 2 items (shoes 100, bed/bath 50), approval 2 h
    o2 (customer u2, AL) delivered 5 days late: 1 item (shoes 200), boleto approved after 24 h
    o3 (customer u1, SP) canceled            : 1 item (bed/bath 80)
    o4 (customer u1, SP) delivered, but PODAT before goods issue -> delivery QUARANTINED
    o5 (customer u2, AL) placed in 2016     -> outside the analysis window

Expected (analysis window 2017-01-01..2018-08-31):
    orders 4, items 5, OTIF 2/4, in-full 3/4, on-time 2/3, cancellation 1/4,
    lead time (5+5+18)/3, promised (9+9+13)/3, revenue 380, approval (2+24+1+1)/4 hours,
    complaint rate 2/4, seller hand-off on time 2/3, fashion revenue share 300/380.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

from src.db import get_engine


def olist_frames() -> dict[str, pd.DataFrame]:
    orders = pd.DataFrame(
        [
            ["o1", "c1", "delivered", "2017-03-01 10:00:00", "2017-03-01 12:00:00",
             "2017-03-03 09:00:00", "2017-03-06 15:00:00", "2017-03-10 00:00:00"],
            ["o2", "c2", "delivered", "2017-03-02 08:00:00", "2017-03-03 08:00:00",
             "2017-03-05 10:00:00", "2017-03-20 10:00:00", "2017-03-15 00:00:00"],
            ["o3", "c3", "canceled", "2017-03-04 08:00:00", "2017-03-04 09:00:00",
             None, None, "2017-03-20 00:00:00"],
            ["o4", "c4", "delivered", "2017-03-05 10:00:00", "2017-03-05 11:00:00",
             "2017-03-10 10:00:00", "2017-03-08 10:00:00", "2017-03-25 00:00:00"],
            ["o5", "c5", "delivered", "2016-10-05 10:00:00", "2016-10-05 11:00:00",
             "2016-10-06 10:00:00", "2016-10-12 10:00:00", "2016-10-30 00:00:00"],
        ],
        columns=["order_id", "customer_id", "order_status", "order_purchase_timestamp",
                 "order_approved_at", "order_delivered_carrier_date",
                 "order_delivered_customer_date", "order_estimated_delivery_date"],
    )
    customers = pd.DataFrame(
        [["c1", "u1", "01001", "sao paulo", "SP"], ["c2", "u2", "57000", "maceio", "AL"],
         ["c3", "u1", "01001", "sao paulo", "SP"], ["c4", "u1", "01001", "sao paulo", "SP"],
         ["c5", "u2", "57000", "maceio", "AL"]],
        columns=["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                 "customer_city", "customer_state"],
    )
    items = pd.DataFrame(
        [["o1", 1, "p1", "s1", "2017-03-04 00:00:00", 100.0, 10.0],
         ["o1", 2, "p2", "s1", "2017-03-02 00:00:00", 50.0, 5.0],
         ["o2", 1, "p1", "s1", "2017-03-06 00:00:00", 200.0, 20.0],
         ["o3", 1, "p2", "s2", "2017-03-06 00:00:00", 80.0, 8.0],
         ["o4", 1, "p3", "s2", "2017-03-08 00:00:00", 30.0, 3.0],
         ["o5", 1, "p2", "s1", "2016-10-07 00:00:00", 40.0, 4.0]],
        columns=["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date",
                 "price", "freight_value"],
    )
    payments = pd.DataFrame(
        [["o1", 1, "credit_card", 2, 165.0], ["o2", 1, "boleto", 1, 220.0],
         ["o3", 1, "credit_card", 1, 88.0], ["o4", 1, "voucher", 1, 33.0],
         ["o5", 1, "credit_card", 1, 44.0]],
        columns=["order_id", "payment_sequential", "payment_type", "payment_installments",
                 "payment_value"],
    )
    reviews = pd.DataFrame(
        [[f"r{i}", f"o{i}", score, "", "", "2017-03-21 00:00:00", "2017-03-22 00:00:00"]
         for i, score in [(1, 5), (2, 1), (3, 2), (4, 4), (5, 3)]],
        columns=["review_id", "order_id", "review_score", "review_comment_title",
                 "review_comment_message", "review_creation_date", "review_answer_timestamp"],
    )
    products = pd.DataFrame(
        [["p1", "fashion_calcados", 40, 300, 2, 500, 30, 10, 20],
         ["p2", "cama_mesa_banho", 40, 300, 2, 900, 40, 10, 30],
         ["p3", None, None, None, None, 200, 10, 10, 10]],
        columns=["product_id", "product_category_name", "product_name_lenght",
                 "product_description_lenght", "product_photos_qty", "product_weight_g",
                 "product_length_cm", "product_height_cm", "product_width_cm"],
    )
    sellers = pd.DataFrame(
        [["s1", "01001", "sao paulo", "SP"], ["s2", "13000", "campinas", "SP"]],
        columns=["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    )
    geolocation = pd.DataFrame(
        [["01001", -23.55, -46.63, "sao paulo", "SP"], ["57000", -9.66, -35.73, "maceio", "AL"]],
        columns=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
                 "geolocation_city", "geolocation_state"],
    )
    translation = pd.DataFrame(
        [["fashion_calcados", "fashion_shoes"], ["cama_mesa_banho", "bed_bath_table"]],
        columns=["product_category_name", "product_category_name_english"],
    )
    return {"orders": orders, "customers": customers, "order_items": items,
            "payments": payments, "reviews": reviews, "products": products,
            "sellers": sellers, "geolocation": geolocation, "category_translation": translation}


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
