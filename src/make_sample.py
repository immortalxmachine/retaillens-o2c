"""Build the small, deterministic REAL sample in data/sample/ (committed, used by CI).

CI must run without Kaggle credentials, so we keep a slice of the real data:
every order whose order_id starts with "0" (order ids are random hex, so this is an unbiased
~1/16 sample) plus ALL rows that belong to those orders (items, payments, reviews) and the
customers, products, sellers and geolocation rows they reference. Same input -> same sample.

Free-text review comments are blanked in the sample (they are not used by any KPI and only
make the file larger).

Run:  python -m src.make_sample      (needs the full download in data/raw/)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_DIR, SAMPLE_DIR
from src.download import OLIST_FILES


def build_sample(raw_dir: Path = RAW_DIR, out_dir: Path = SAMPLE_DIR, prefix: str = "0") -> dict:
    def read(name: str) -> pd.DataFrame:
        return pd.read_csv(raw_dir / OLIST_FILES[name], dtype=str)

    orders = read("orders")
    orders = orders[orders.order_id.str.startswith(prefix)].sort_values("order_id")
    keep = set(orders.order_id)
    items = read("order_items").pipe(lambda d: d[d.order_id.isin(keep)])
    payments = read("payments").pipe(lambda d: d[d.order_id.isin(keep)])
    reviews = read("reviews").pipe(lambda d: d[d.order_id.isin(keep)]).assign(
        review_comment_title="", review_comment_message="")
    customers = read("customers").pipe(lambda d: d[d.customer_id.isin(orders.customer_id)])
    products = read("products").pipe(lambda d: d[d.product_id.isin(items.product_id)])
    sellers = read("sellers").pipe(lambda d: d[d.seller_id.isin(items.seller_id)])
    zips = set(customers.customer_zip_code_prefix) | set(sellers.seller_zip_code_prefix)
    geo = read("geolocation")
    # one (the first) geolocation row per zip prefix is enough for the mapping
    geo = geo[geo.geolocation_zip_code_prefix.isin(zips)].drop_duplicates(
        "geolocation_zip_code_prefix")

    frames = {"orders": orders, "order_items": items, "payments": payments, "reviews": reviews,
              "customers": customers, "products": products, "sellers": sellers,
              "geolocation": geo, "category_translation": read("category_translation")}
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        df.to_csv(out_dir / OLIST_FILES[name], index=False)
    return {name: len(df) for name, df in frames.items()}


if __name__ == "__main__":
    for table, rows in build_sample().items():
        print(f"{table:22s} {rows:>7,d}")
