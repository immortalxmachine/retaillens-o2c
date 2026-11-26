"""Stage 1 - load the SAP-structured tables into staging tables stg_<table>.

On PostgreSQL this would usually be a separate `staging` schema. We use a stg_ prefix instead so
the identical SQL also runs on SQLite (which has no schemas). Column names are lower-cased because
PostgreSQL folds unquoted identifiers to lower case (VBELN -> vbeln).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from src.db import write_table

TABLES = ["kna1", "lfa1", "mara", "t023t", "vbak", "vbap", "likp", "lips", "bsad", "zreview",
          "zgeo"]

# date / timestamp fields of the mapped tables
DATE_COLUMNS = ["ERDAT", "VDATU", "LFDAT", "WADAT_IST", "PODAT", "WADAT", "AUGDT", "CREATED",
                "ANSWERED"]


def load_staging(engine: Engine, tables: dict[str, pd.DataFrame]) -> dict:
    """Write every table to stg_<name>. Returns {table: row_count} for the run log."""
    counts = {}
    for name in TABLES:
        df = tables[name].copy()
        for col in DATE_COLUMNS:  # make sure dates are real datetimes (missing -> NaT)
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        df.columns = [c.lower() for c in df.columns]
        write_table(engine, df, f"stg_{name}")
        counts[name] = len(df)
    return counts
