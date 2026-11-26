"""Stage 2 - data-quality checks on the staging tables.

Design: rules are plain data (dicts below), one generic function applies them. Rows that pass go
to cln_<table>; rows that fail go to dq_quarantine with the rule and a human-readable reason, so
nothing is silently dropped. Every run appends row counts to dq_run_log.

Rule types
  mandatory     - column must not be NULL                     (e.g. VBAK.ERDAT)
  non_negative  - numeric column must be >= 0                 (e.g. VBAP.KWMENG)
  reference     - child key must exist in the CLEAN parent    (e.g. VBAP.VBELN -> VBAK.VBELN)
Parents are checked before children, so an item whose header was quarantined is quarantined too.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.engine import Engine

from src.db import query, write_table
from src.load import DATE_COLUMNS

# Business key of each table (used to identify a quarantined record)
KEYS = {
    "kna1": ["kunnr"], "mara": ["matnr"], "makt": ["matnr"],
    "vbak": ["vbeln"], "vbap": ["vbeln", "posnr"],
    "likp": ["vbeln"], "lips": ["vbeln", "posnr"],
    "vbrk": ["vbeln"], "vbrp": ["vbeln", "posnr"],
    "bsad": ["belnr"], "returns": ["vbeln", "posnr"],
}

MANDATORY = {
    "kna1": ["kunnr", "land1"],
    "mara": ["matnr", "matkl"],
    "vbak": ["vbeln", "erdat", "vdatu", "kunnr"],
    "vbap": ["vbeln", "posnr", "matnr", "kwmeng", "netwr"],
    "likp": ["vbeln", "wadat_ist"],
    "lips": ["vbeln", "posnr", "lfimg", "vgbel", "vgpos"],
    "vbrk": ["vbeln", "fkdat"],
    "vbrp": ["vbeln", "posnr", "fkimg", "netwr"],
    "bsad": ["belnr", "vbeln", "augdt"],
    "returns": ["vbeln", "kwmeng", "vgbel", "vgpos"],
}

NON_NEGATIVE = {
    "vbap": ["kwmeng", "netwr"],
    "lips": ["lfimg"],
    "vbrp": ["fkimg", "netwr"],
    "bsad": ["dmbtr"],
    "returns": ["kwmeng", "netwr"],
}

# (child table, child column, parent table, parent column)
REFERENCES = [
    ("vbak", "kunnr", "kna1", "kunnr"),
    ("vbap", "vbeln", "vbak", "vbeln"),
    ("vbap", "matnr", "mara", "matnr"),
    ("lips", "vbeln", "likp", "vbeln"),
    ("vbrp", "vbeln", "vbrk", "vbeln"),
]

# Parents first, so references are checked against already-cleaned parents
ORDER = ["kna1", "mara", "makt", "vbak", "vbap", "likp", "lips", "vbrk", "vbrp", "bsad", "returns"]


def check_table(
    df: pd.DataFrame, table: str, clean: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply all rules for one table. Returns (passed_rows, quarantine_rows)."""
    failures = []  # one entry per (record, rule)

    def flag(mask: pd.Series, rule: str, reason: str) -> None:
        for idx in df.index[mask]:
            failures.append({"idx": idx, "rule": rule, "reason": reason})

    for col in MANDATORY.get(table, []):
        flag(df[col].isna(), "mandatory", f"{table.upper()}.{col.upper()} is missing")
    for col in NON_NEGATIVE.get(table, []):
        flag(df[col] < 0, "non_negative", f"{table.upper()}.{col.upper()} is negative")
    for child, ccol, parent, pcol in REFERENCES:
        if child == table:
            ok = df[ccol].isin(clean[parent][pcol])
            flag(~ok, "reference", f"{child.upper()}.{ccol.upper()} has no valid "
                                   f"{parent.upper()}.{pcol.upper()} (orphan)")

    bad_idx = sorted({f["idx"] for f in failures})
    passed = df.drop(index=bad_idx)

    quarantine = pd.DataFrame(
        [
            {
                "source_table": table,
                "record_key": "|".join(str(df.at[f["idx"], k]) for k in KEYS[table]),
                "rule": f["rule"],
                "reason": f["reason"],
                # keep the full raw record as JSON so it can be fixed and re-loaded later
                "raw_record": df.loc[f["idx"]].to_json(date_format="iso"),
            }
            for f in failures
        ],
        columns=["source_table", "record_key", "rule", "reason", "raw_record"],
    )
    return passed, quarantine


def _read_staging(engine: Engine, table: str) -> pd.DataFrame:
    df = query(engine, f"SELECT * FROM stg_{table}")
    # SQLite returns dates as text -> convert back to datetime
    for col in (c.lower() for c in DATE_COLUMNS):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def run_dq(engine: Engine) -> dict:
    """Check every staging table, write cln_*, dq_quarantine and append to dq_run_log."""
    run_id = uuid.uuid4().hex[:8]
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    clean: dict[str, pd.DataFrame] = {}
    quarantines, log_rows = [], []

    for table in ORDER:
        raw = _read_staging(engine, table)
        passed, quarantine = check_table(raw, table, clean)
        clean[table] = passed
        write_table(engine, passed, f"cln_{table}")
        quarantines.append(quarantine)
        log_rows.append(
            {"run_id": run_id, "run_ts": run_ts, "source_table": table, "rows_in": len(raw),
             "rows_passed": len(passed), "rows_quarantined": len(raw) - len(passed)}
        )

    all_q = pd.concat(quarantines, ignore_index=True)
    all_q.insert(0, "run_id", run_id)
    write_table(engine, all_q, "dq_quarantine")

    # The run log is appended (history of runs), not replaced
    pd.DataFrame(log_rows).to_sql("dq_run_log", engine, if_exists="append", index=False)

    by_rule = all_q.groupby(["source_table", "rule"]).size()
    return {
        "run_id": run_id,
        "rows_in": int(sum(r["rows_in"] for r in log_rows)),
        "rows_passed": int(sum(r["rows_passed"] for r in log_rows)),
        "rows_quarantined": int(sum(r["rows_quarantined"] for r in log_rows)),
        "quarantine_by_table": {r["source_table"]: r["rows_quarantined"] for r in log_rows
                                if r["rows_quarantined"]},
        "violations_by_rule": {f"{t}.{r}": int(n) for (t, r), n in by_rule.items()},
    }


if __name__ == "__main__":
    from src.db import get_engine

    print(json.dumps(run_dq(get_engine()), indent=2))
