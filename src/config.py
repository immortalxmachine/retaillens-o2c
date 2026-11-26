"""Central settings for RetailLens: paths, analysis window and database connection.

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
# Full Olist download (gitignored). CI points RETAILLENS_RAW_DIR at the committed sample instead.
RAW_DIR = Path(os.getenv("RETAILLENS_RAW_DIR", DATA_DIR / "raw"))
if not RAW_DIR.is_absolute():
    RAW_DIR = ROOT / RAW_DIR
SAMPLE_DIR = DATA_DIR / "sample"  # small deterministic REAL sample, committed for CI/tests
SQL_DIR = ROOT / "sql"  # star-schema views (CDS-style)
KPI_SQL_DIR = SQL_DIR / "kpi"  # one KPI query per file
POWERBI_DIR = ROOT / "powerbi"
REPORTS_DIR = ROOT / "reports"
METRICS_PATH = ROOT / "metrics.json"

# Kaggle dataset used for the case study (licence CC BY-NC-SA 4.0 - non-commercial use only)
KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
SOURCE_NOTICE = (
    "Source: Olist Brazilian E-Commerce Public Dataset (Kaggle olistbr/brazilian-ecommerce), "
    "CC BY-NC-SA 4.0 - real anonymised orders, mapped to SAP S/4HANA SD structures for a case study"
)

# KPIs use complete months only: Olist has a handful of test orders in late 2016 and the
# extract ends mid-September 2018 with mostly unfinished orders.
ANALYSIS_START = os.getenv("RETAILLENS_START", "2017-01-01")
ANALYSIS_END = os.getenv("RETAILLENS_END", "2018-08-31")

# PostgreSQL when DATABASE_URL is set (Docker / CI), otherwise a local SQLite file
DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'retaillens.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
