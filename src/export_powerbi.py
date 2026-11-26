"""Stage 5a - export the star schema for Power BI Desktop (CSV + Parquet in powerbi/data/).

Power BI imports these files (join facts to dim_date on date_key); relationships and DAX
measures are described in
powerbi/BUILD_STEPS.md and powerbi/DAX_measures.md.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from src.config import POWERBI_DIR
from src.db import query
from src.star_schema import STAR_VIEWS

# date / timestamp columns of the star-schema views (SQLite returns them as text)
VIEW_DATE_COLUMNS = {
    "calendar_date", "order_ts", "promised_date", "approved_ts", "gi_ts", "pod_ts",
    "ship_limit_ts",
}


def export_star_schema(engine: Engine) -> dict[str, int]:
    """Write every dim/fact view to CSV and Parquet. Returns {table: rows}."""
    out = POWERBI_DIR / "data"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for logical, view in STAR_VIEWS.items():
        df = query(engine, f"SELECT * FROM {view}")
        for col in df.columns:
            if col in VIEW_DATE_COLUMNS:
                df[col] = pd.to_datetime(df[col])  # real datetime type in Parquet / CSV
        df.to_csv(out / f"{logical}.csv", index=False)
        df.to_parquet(out / f"{logical}.parquet", index=False)
        counts[logical] = len(df)
    return counts
