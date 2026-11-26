"""Stage 5a - export the star schema for Power BI Desktop (CSV + Parquet in powerbi/data/).

Power BI imports these files; relationships and DAX measures are described in
powerbi/BUILD_STEPS.md and powerbi/DAX_measures.md.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from src.config import POWERBI_DIR
from src.db import query
from src.load import DATE_COLUMNS
from src.star_schema import STAR_VIEWS

# date columns of the star-schema views (renamed from the SAP names)
VIEW_DATE_COLUMNS = {
    "calendar_date", "order_date", "requested_date", "first_gi_date", "last_gi_date",
    "planned_date", "goods_issue_date", "billing_date", "clearing_date",
}


def export_star_schema(engine: Engine) -> dict[str, int]:
    """Write every dim/fact view to CSV and Parquet. Returns {table: rows}."""
    out = POWERBI_DIR / "data"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for logical, view in STAR_VIEWS.items():
        df = query(engine, f"SELECT * FROM {view}")
        for col in df.columns:
            if col in VIEW_DATE_COLUMNS or col.upper() in DATE_COLUMNS:
                # plain dates (no time part) so Power BI detects a Date column
                df[col] = pd.to_datetime(df[col]).dt.date
        df.to_csv(out / f"{logical}.csv", index=False)
        df.to_parquet(out / f"{logical}.parquet", index=False)
        counts[logical] = len(df)
    return counts
