"""Stage 4 - run the O2C KPI queries in sql/kpi/*.sql.

Each file is one SELECT. The result is stored as table kpi_<name> (so dashboards can read it
straight from the database) and as reports/kpi/<name>.csv (so reviewers can see it on GitHub).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine

from src.config import KPI_SQL_DIR, REPORTS_DIR
from src.db import query, write_table


def kpi_name(path) -> str:
    """'03_otif_monthly.sql' -> 'otif_monthly'."""
    return path.stem.split("_", 1)[1]


def _to_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """PostgreSQL returns NUMERIC as Python Decimal - convert those columns to float."""
    for col in df.columns:
        if df[col].dtype == object:
            converted = pd.to_numeric(df[col], errors="coerce")
            # only convert when every non-null value really was numeric
            if converted.notna().sum() == df[col].notna().sum():
                df[col] = converted
    return df


def run_kpis(engine: Engine, write_csv: bool = True) -> dict[str, pd.DataFrame]:
    """Execute every KPI query and return {kpi_name: DataFrame}."""
    results = {}
    out_dir = REPORTS_DIR / "kpi"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(KPI_SQL_DIR.glob("*.sql")):
        name = kpi_name(path)
        df = _to_numbers(query(engine, path.read_text(encoding="utf-8")))
        write_table(engine, df, f"kpi_{name}")
        if write_csv:
            df.round(4).to_csv(out_dir / f"{name}.csv", index=False)
        results[name] = df
    return results


if __name__ == "__main__":
    from src.db import get_engine

    for name, frame in run_kpis(get_engine()).items():
        print(f"\n== {name} ==\n{frame.head(10).to_string(index=False)}")
