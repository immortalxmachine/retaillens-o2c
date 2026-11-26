"""Stage 1 - load the raw SAP extracts (CSV) into staging tables stg_<table>.

On PostgreSQL this would usually be a separate `staging` schema. We use a stg_ prefix instead so
the identical SQL also runs on SQLite (which has no schemas). Column names are lower-cased because
PostgreSQL folds unquoted identifiers to lower case (VBELN -> vbeln).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from src.config import RAW_DIR
from src.db import write_table

TABLES = ["kna1", "mara", "makt", "vbak", "vbap", "likp", "lips", "vbrk", "vbrp", "bsad", "returns"]

# SAP document / master keys are zero-padded strings - never let pandas turn them into numbers
KEY_COLUMNS = ["KUNNR", "KUNAG", "MATNR", "VBELN", "VGBEL", "AUBEL", "BELNR", "VKORG"]
DATE_COLUMNS = ["ERDAT", "VDATU", "LFDAT", "WADAT_IST", "FKDAT", "AUGDT"]


def read_raw(name: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Read one extract with correct types (keys as text, dates as datetime)."""
    path = raw_dir / f"{name}.csv"
    header = pd.read_csv(path, nrows=0).columns
    dtypes = {c: str for c in header if c in KEY_COLUMNS}
    dates = [c for c in header if c in DATE_COLUMNS]
    return pd.read_csv(path, dtype=dtypes, parse_dates=dates)


def load_staging(engine: Engine, tables: dict[str, pd.DataFrame] | None = None) -> dict:
    """Write every table to stg_<name>. Returns {table: row_count} for the run log."""
    counts = {}
    for name in TABLES:
        df = tables[name] if tables is not None else read_raw(name)
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        write_table(engine, df, f"stg_{name}")
        counts[name] = len(df)
    return counts
