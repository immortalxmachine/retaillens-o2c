"""Database helpers shared by every pipeline stage.

The same SQL must run on PostgreSQL (Docker / CI) and SQLite (local fallback). The only real
difference we need is date arithmetic, so the SQL files use one tiny macro, DAYS_BETWEEN(a, b),
which render_sql() translates into the right dialect.
"""

from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL

# DAYS_BETWEEN(start, end) -> number of days from start to end (arguments must be simple columns)
_DAYS_BETWEEN = re.compile(r"DAYS_BETWEEN\(\s*([\w.]+)\s*,\s*([\w.]+)\s*\)")


def get_engine(url: str = DATABASE_URL) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL or SQLite."""
    return create_engine(url)


def render_sql(sql: str, dialect: str) -> str:
    """Translate the DAYS_BETWEEN macro for the target database."""
    if dialect == "postgresql":
        # DATE - DATE gives an integer number of days in PostgreSQL
        return _DAYS_BETWEEN.sub(r"(CAST(\2 AS DATE) - CAST(\1 AS DATE))", sql)
    # SQLite stores dates as text; julianday() turns them into day numbers
    return _DAYS_BETWEEN.sub(r"CAST(julianday(\2) - julianday(\1) AS INTEGER)", sql)


def run_statements(engine: Engine, sql: str) -> None:
    """Execute a script that may contain several ';'-separated statements."""
    sql = render_sql(sql, engine.dialect.name)
    with engine.begin() as conn:
        for stmt in sql.split(";"):
            # skip chunks that are only comments / whitespace
            body = "\n".join(
                line for line in stmt.splitlines() if not line.strip().startswith("--")
            )
            if body.strip():
                conn.execute(text(stmt))


def query(engine: Engine, sql: str) -> pd.DataFrame:
    """Run one SELECT (with the macro rendered) and return a DataFrame."""
    return pd.read_sql(text(render_sql(sql, engine.dialect.name)), engine)


def write_table(engine: Engine, df: pd.DataFrame, name: str) -> None:
    """Replace a table with the DataFrame contents."""
    df.to_sql(name, engine, if_exists="replace", index=False, chunksize=1000, method="multi")
