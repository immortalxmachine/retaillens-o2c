"""Map the real Olist CSVs into SAP S/4HANA SD table structures (case study).

Olist is a Brazilian marketplace, not an SAP system - so this module is the "extraction layer"
of the case study: it renames and reshapes the real data into the tables an SAP consultant
would query. The full field-by-field mapping and its assumptions are in docs/sap_mapping.md.

    customers     -> KNA1   customer master (KUNNR = customer_unique_id, REGIO = state)
    sellers       -> LFA1   vendor master (marketplace sellers)
    products      -> MARA   material master (MATKL = Olist category code)
    translation   -> T023T  material group texts (English category names)
    orders        -> VBAK   sales order header (ERDAT = purchase, VDATU = estimated delivery)
    order_items   -> VBAP   sales order items (one Olist item row = one piece)
    orders/items  -> LIKP/LIPS  outbound delivery (WADAT_IST = carrier hand-off,
                                PODAT = delivered to customer, LIPS.WADAT = seller ship-by date)
    payments      -> BSAD   cleared customer payments (AUGDT = payment approval)
    reviews       -> ZREVIEW  customer reviews (custom Z-table: no SD standard table exists)
    geolocation   -> ZGEO   one row per zip prefix (custom Z-table, used for DQ)

Nothing is invented: rows without a source value stay NULL and are handled by the DQ stage.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_DIR
from src.download import OLIST_FILES

ORDER_DATES = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"]


def read_olist(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Read the nine Olist CSVs; ids and zip prefixes stay text (leading zeros!)."""
    frames = {}
    for name, file in OLIST_FILES.items():
        frames[name] = pd.read_csv(
            raw_dir / file,
            dtype={"customer_zip_code_prefix": str, "seller_zip_code_prefix": str,
                   "geolocation_zip_code_prefix": str},
        )
    return frames


def _zip(s: pd.Series) -> pd.Series:
    """Zip prefixes are 5 digits; CSV tools sometimes drop the leading zero."""
    return s.astype(str).str.zfill(5)


def map_to_sap(o: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    orders = o["orders"].copy()
    for col in ORDER_DATES:
        orders[col] = pd.to_datetime(orders[col])
    cust = o["customers"].copy()
    cust["customer_zip_code_prefix"] = _zip(cust["customer_zip_code_prefix"])

    # ---- KNA1: one row per real person (customer_unique_id). Olist issues a new customer_id
    # per order, so customer_id -> customer_unique_id is the sold-to mapping for VBAK.
    kna1 = (cust.sort_values("customer_id").drop_duplicates("customer_unique_id")
            .rename(columns={"customer_unique_id": "KUNNR", "customer_city": "ORT01",
                             "customer_state": "REGIO", "customer_zip_code_prefix": "PSTLZ"})
            .assign(LAND1="BR")[["KUNNR", "LAND1", "REGIO", "ORT01", "PSTLZ"]])
    sold_to = cust.set_index("customer_id")["customer_unique_id"]

    # ---- LFA1: sellers as vendor master
    sel = o["sellers"].copy()
    lfa1 = (sel.assign(seller_zip_code_prefix=_zip(sel["seller_zip_code_prefix"]), LAND1="BR")
            .rename(columns={"seller_id": "LIFNR", "seller_city": "ORT01",
                             "seller_state": "REGIO", "seller_zip_code_prefix": "PSTLZ"})
            [["LIFNR", "LAND1", "REGIO", "ORT01", "PSTLZ"]])

    # ---- MARA + T023T: material master and material-group (category) texts
    p = o["products"]
    mara = pd.DataFrame({
        "MATNR": p["product_id"], "MATKL": p["product_category_name"], "MTART": "HAWA",
        "BRGEW": p["product_weight_g"], "GEWEI": "G", "LAENG": p["product_length_cm"],
        "BREIT": p["product_width_cm"], "HOEHE": p["product_height_cm"], "MEABM": "CM"})
    t = o["category_translation"]
    t023t = pd.DataFrame({"MATKL": t["product_category_name"], "SPRAS": "E",
                          "WGBEZ": t["product_category_name_english"]})

    # ---- VBAP: sales order items
    items = o["order_items"].copy()
    items["shipping_limit_date"] = pd.to_datetime(items["shipping_limit_date"])
    vbap = pd.DataFrame({
        "VBELN": items["order_id"], "POSNR": items["order_item_id"].astype(int),
        "MATNR": items["product_id"], "ZZLIFNR": items["seller_id"], "KWMENG": 1,
        "VRKME": "ST", "NETWR": items["price"], "ZZFREIGHT": items["freight_value"],
        "WAERK": "BRL"})

    # ---- VBAK: sales order header
    netwr = vbap.groupby("VBELN")["NETWR"].sum()
    vbak = pd.DataFrame({
        "VBELN": orders["order_id"], "AUART": "OR",
        "ERDAT": orders["order_purchase_timestamp"],  # created on (date + time)
        "KUNNR": orders["customer_id"].map(sold_to),
        "VDATU": orders["order_estimated_delivery_date"],  # date promised to the customer
        "ZZSTATUS": orders["order_status"],  # Olist status (delivered, canceled, ...)
        "NETWR": orders["order_id"].map(netwr).round(2), "WAERK": "BRL"})

    # ---- LIKP/LIPS: an outbound delivery exists once the order left the seller or arrived
    shipped = orders[orders["order_delivered_carrier_date"].notna()
                     | orders["order_delivered_customer_date"].notna()
                     | orders["order_status"].isin(["shipped", "delivered"])]
    likp = pd.DataFrame({
        "VBELN": shipped["order_id"],  # Olist ships one consignment per order
        "KUNNR": shipped["customer_id"].map(sold_to),
        "LFDAT": shipped["order_estimated_delivery_date"],
        "WADAT_IST": shipped["order_delivered_carrier_date"],  # actual goods issue
        "PODAT": shipped["order_delivered_customer_date"]})  # proof of delivery
    ship_items = items[items["order_id"].isin(shipped["order_id"])]
    lips = pd.DataFrame({
        "VBELN": ship_items["order_id"], "POSNR": ship_items["order_item_id"].astype(int),
        "MATNR": ship_items["product_id"], "ZZLIFNR": ship_items["seller_id"], "LFIMG": 1,
        "VGBEL": ship_items["order_id"], "VGPOS": ship_items["order_item_id"].astype(int),
        "WADAT": ship_items["shipping_limit_date"]})  # seller's ship-by date (planned GI)

    # ---- BSAD: one cleared item per payment line; AUGDT = payment approval timestamp
    pay = o["payments"]
    approved = orders.set_index("order_id")["order_approved_at"]
    kunnr = orders.set_index("order_id")["customer_id"].map(sold_to)
    bsad = pd.DataFrame({
        "BELNR": pay["order_id"] + "-" + pay["payment_sequential"].astype(str),
        "VBELN": pay["order_id"], "KUNNR": pay["order_id"].map(kunnr),
        "ZLSCH": pay["payment_type"], "ZZINSTALLMENTS": pay["payment_installments"],
        "DMBTR": pay["payment_value"], "WAERS": "BRL", "AUGDT": pay["order_id"].map(approved)})

    # ---- ZREVIEW: customer reviews (no standard SD table - custom Z-table)
    r = o["reviews"]
    zreview = pd.DataFrame({
        "REVIEW_ID": r["review_id"], "VBELN": r["order_id"],
        "SCORE": r["review_score"].astype(int),
        "CREATED": pd.to_datetime(r["review_creation_date"]),
        "ANSWERED": pd.to_datetime(r["review_answer_timestamp"]),
        "HAS_COMMENT": r["review_comment_message"].fillna("").str.strip().ne("").astype(int)})

    # ---- ZGEO: one row per zip prefix (mean coordinates, most frequent state)
    g = o["geolocation"].copy()
    g["geolocation_zip_code_prefix"] = _zip(g["geolocation_zip_code_prefix"])
    zgeo = (g.groupby("geolocation_zip_code_prefix")
            .agg(LAT=("geolocation_lat", "mean"), LNG=("geolocation_lng", "mean"),
                 REGIO=("geolocation_state", lambda s: s.mode().iloc[0]))
            .reset_index().rename(columns={"geolocation_zip_code_prefix": "PSTLZ"}))

    return {"kna1": kna1, "lfa1": lfa1, "mara": mara, "t023t": t023t, "vbak": vbak,
            "vbap": vbap, "likp": likp, "lips": lips, "bsad": bsad, "zreview": zreview,
            "zgeo": zgeo}


if __name__ == "__main__":
    for name, df in map_to_sap(read_olist()).items():
        print(f"{name:8s} {len(df):>8,d} rows")
