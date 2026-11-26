"""Database helpers shared by every pipeline stage.

The same SQL must run on PostgreSQL (Docker / CI) and SQLite (local fallback). The only real
differences we need are date functions, so the SQL files use three tiny macros which
render_sql() translates into the right dialect:

    DAYS_BETWEEN(a, b)   whole calendar days from a to b (time of day ignored)
    HOURS_BETWEEN(a, b)  hours (with decimals) from timestamp a to timestamp b
    DATE_KEY(a)          'YYYY-MM-DD' text, used to join timestamps to the calendar view
"""

from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL

# macro arguments must be simple column references like f.order_ts
_ARG = r"\s*([\w.]+)\s*"
_DAYS = re.compile(rf"DAYS_BETWEEN\({_ARG},{_ARG}\)")
_HOURS = re.compile(rf"HOURS_BETWEEN\({_ARG},{_ARG}\)")
_DATE_KEY = re.compile(rf"DATE_KEY\({_ARG}\)")

MACROS = {
    "postgresql": [
        # DATE - DATE gives an integer number of days in PostgreSQL
        (_DAYS, r"(CAST(\2 AS DATE) - CAST(\1 AS DATE))"),
        (_HOURS, r"(EXTRACT(EPOCH FROM (CAST(\2 AS TIMESTAMP) - CAST(\1 AS TIMESTAMP))) / 3600.0)"),
        (_DATE_KEY, r"TO_CHAR(\1, 'YYYY-MM-DD')"),
    ],
    "sqlite": [
        # SQLite stores timestamps as text; julianday() turns them into day numbers
        (_DAYS, r"CAST(julianday(date(\2)) - julianday(date(\1)) AS INTEGER)"),
        (_HOURS, r"((julianday(\2) - julianday(\1)) * 24.0)"),
        (_DATE_KEY, r"strftime('%Y-%m-%d', \1)"),
    ],
}


def get_engine(url: str = DATABASE_URL) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL or SQLite."""
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        # keep SQLite's sort/temp tables in memory instead of the system temp folder
        @event.listens_for(engine, "connect")
        def _pragma(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA temp_store = MEMORY")

    return engine


def render_sql(sql: str, dialect: str) -> str:
    """Translate the date macros for the target database."""
    for pattern, replacement in MACROS["postgresql" if dialect == "postgresql" else "sqlite"]:
        sql = pattern.sub(replacement, sql)
    return sql


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
    """Run one SELECT (with the macros rendered) and return a DataFrame."""
    return pd.read_sql(text(render_sql(sql, engine.dialect.name)), engine)


def write_table(engine: Engine, df: pd.DataFrame, name: str) -> None:
    """Replace a table with the DataFrame contents."""
    # multi-row INSERTs are fastest on PostgreSQL; SQLite is fastest with plain executemany
    method = "multi" if engine.dialect.name == "postgresql" else None
    df.to_sql(name, engine, if_exists="replace", index=False, chunksize=1000, method=method)
