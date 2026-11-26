"""Download the Olist Brazilian E-Commerce dataset from Kaggle into data/raw/.

Source : https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
Licence: CC BY-NC-SA 4.0 (attribution, non-commercial, share-alike)

Authentication uses the Kaggle CLI's own credential file in the user's home folder; this code
never reads, prints or stores the token.

Run:  python -m src.download
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.config import KAGGLE_DATASET, RAW_DIR

# The nine CSV files the case study uses
OLIST_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def is_present(raw_dir: Path = RAW_DIR) -> bool:
    return all((raw_dir / f).exists() for f in OLIST_FILES.values())


def download(raw_dir: Path = RAW_DIR) -> None:
    """Call the Kaggle CLI (installed in the venv) unless the files are already there."""
    if is_present(raw_dir):
        print(f"Olist files already in {raw_dir}")
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    kaggle = Path(sys.executable).with_name("kaggle")  # kaggle(.exe) next to python
    cmd = [str(kaggle), "datasets", "download", "-d", KAGGLE_DATASET, "-p", str(raw_dir),
           "--unzip"]
    subprocess.run(cmd, check=True)
    if not is_present(raw_dir):
        raise FileNotFoundError(f"Download finished but files are missing in {raw_dir}")


if __name__ == "__main__":
    download()
