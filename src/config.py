"""Central settings for RetailLens: paths, seed and database connection.

Everything that might change between laptop, Docker and CI lives here, so the
rest of the code never hard-codes a path or a password.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that contains src/
ROOT = Path(__file__).resolve().parents[1]

# Read .env if it exists (secrets stay out of git; see .env.example)
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # generated SAP-style CSV extracts land here
SQL_DIR = ROOT / "sql"  # star-schema views (CDS-style)
KPI_SQL_DIR = SQL_DIR / "kpi"  # one KPI query per file
POWERBI_DIR = ROOT / "powerbi"
REPORTS_DIR = ROOT / "reports"
METRICS_PATH = ROOT / "metrics.json"

# One seed drives the whole synthetic dataset -> identical data on every run
SEED = int(os.getenv("RETAILLENS_SEED", "42"))

# PostgreSQL when DATABASE_URL is set (Docker / CI), otherwise a local SQLite file
DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'retaillens.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
