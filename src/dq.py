"""Stage 2 - data-quality checks on the staging tables (real issues found in the Olist data).

Design: every rule is one entry in RULES (table, rule type, severity, reason, check function).
One generic loop applies them.

  severity "error"   -> the row is QUARANTINED: it goes to dq_quarantine, not to cln_<table>
  severity "warning" -> the row is kept in cln_<table>, the issue is logged in dq_quarantine

Rule types: mandatory (NOT NULL), non_negative, reference (key must exist in the CLEAN parent),
consistency (cross-field / cross-table business logic, e.g. delivered before it was shipped).
Parents are checked before children, so items of a quarantined header are quarantined too.
Every run appends row counts to dq_run_log.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.engine import Engine

from src.db import query, write_table
from src.load import DATE_COLUMNS

# Business key of each table (used to identify a logged record)
KEYS = {
    "zgeo": ["pstlz"], "t023t": ["matkl"], "kna1": ["kunnr"], "lfa1": ["lifnr"],
    "mara": ["matnr"], "vbak": ["vbeln"], "vbap": ["vbeln", "posnr"], "likp": ["vbeln"],
    "lips": ["vbeln", "posnr"], "bsad": ["belnr"], "zreview": ["review_id", "vbeln"],
}

# Parents first, so references are checked against already-cleaned parents
ORDER = ["zgeo", "t023t", "kna1", "lfa1", "mara", "vbak", "vbap", "likp", "lips", "bsad",
         "zreview"]


# ---------------------------------------------------------------- rule builders
def mandatory(table, cols, severity="error", reason=None):
    names = "/".join(c.upper() for c in cols)
    return {"table": table, "rule": "mandatory", "severity": severity,
            "reason": reason or f"{table.upper()}.{names} is missing",
            "check": lambda df, ctx: df[cols].isna().any(axis=1)}


def non_negative(table, col):
    return {"table": table, "rule": "non_negative", "severity": "error",
            "reason": f"{table.upper()}.{col.upper()} is negative",
            "check": lambda df, ctx: df[col] < 0}


def reference(table, col, parent, pcol, severity="error", reason=None):
    def check(df, ctx):
        known = ctx["clean"][parent][pcol]
        return df[col].notna() & ~df[col].isin(known)
    return {"table": table, "rule": "reference", "severity": severity,
            "reason": reason or f"{table.upper()}.{col.upper()} not found in {parent.upper()}"
                                f" (orphan)",
            "check": check}


def consistency(table, severity, reason, check):
    return {"table": table, "rule": "consistency", "severity": severity, "reason": reason,
            "check": check}


def _order_attr(ctx, col):
    """Lookup Series: order number -> column of the clean VBAK."""
    return ctx["clean"]["vbak"].set_index("vbeln")[col]


RULES = [
    mandatory("kna1", ["kunnr", "regio"]),
    reference("kna1", "pstlz", "zgeo", "pstlz", severity="warning"),
    mandatory("lfa1", ["lifnr"]),
    reference("lfa1", "pstlz", "zgeo", "pstlz", severity="warning"),
    mandatory("mara", ["matnr"]),
    mandatory("mara", ["matkl"], "warning", "MARA.MATKL (product category) is missing"),
    mandatory("mara", ["brgew", "laeng", "breit", "hoehe"], "warning",
              "MARA weight/dimensions are missing"),
    reference("mara", "matkl", "t023t", "matkl", severity="warning",
              reason="MARA.MATKL has no English text in T023T"),
    mandatory("vbak", ["vbeln", "erdat", "kunnr", "vdatu"]),
    reference("vbak", "kunnr", "kna1", "kunnr"),
    consistency("vbak", "warning", "VBAK order has no items (VBAP)",
                lambda df, ctx: ~df["vbeln"].isin(ctx["raw"]["vbap"]["vbeln"])),
    consistency("vbak", "warning", "VBAK order has no payment (BSAD)",
                lambda df, ctx: ~df["vbeln"].isin(ctx["raw"]["bsad"]["vbeln"])),
    mandatory("vbap", ["vbeln", "posnr", "matnr", "netwr"]),
    non_negative("vbap", "netwr"),
    non_negative("vbap", "zzfreight"),
    reference("vbap", "vbeln", "vbak", "vbeln"),
    reference("vbap", "matnr", "mara", "matnr"),
    reference("vbap", "zzlifnr", "lfa1", "lifnr"),
    mandatory("likp", ["vbeln"]),
    reference("likp", "vbeln", "vbak", "vbeln"),
    consistency("likp", "error", "LIKP status delivered but proof of delivery PODAT missing",
                lambda df, ctx: df["vbeln"].map(_order_attr(ctx, "zzstatus")).eq("delivered")
                & df["podat"].isna()),
    consistency("likp", "error", "LIKP status delivered but goods issue WADAT_IST missing",
                lambda df, ctx: df["vbeln"].map(_order_attr(ctx, "zzstatus")).eq("delivered")
                & df["wadat_ist"].isna()),
    consistency("likp", "error", "LIKP goods issue WADAT_IST before order date VBAK.ERDAT",
                lambda df, ctx: df["wadat_ist"] < df["vbeln"].map(_order_attr(ctx, "erdat"))),
    consistency("likp", "error", "LIKP proof of delivery PODAT before goods issue WADAT_IST",
                lambda df, ctx: df["podat"] < df["wadat_ist"]),
    mandatory("lips", ["vbeln", "vgbel", "vgpos"]),
    reference("lips", "vbeln", "likp", "vbeln"),
    mandatory("bsad", ["belnr", "vbeln", "dmbtr"]),
    non_negative("bsad", "dmbtr"),
    reference("bsad", "vbeln", "vbak", "vbeln"),
    consistency("bsad", "warning", "BSAD payment amount DMBTR is zero",
                lambda df, ctx: df["dmbtr"] == 0),
    mandatory("zreview", ["review_id", "vbeln", "score"]),
    reference("zreview", "vbeln", "vbak", "vbeln"),
    consistency("zreview", "warning", "ZREVIEW review_id used for more than one order",
                lambda df, ctx: df["review_id"].duplicated(keep=False)),
]


def check_table(df: pd.DataFrame, table: str, ctx: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply all rules for one table. Returns (rows kept, issue log rows)."""
    issues = []
    error_idx: set = set()
    for r in (r for r in RULES if r["table"] == table):
        mask = r["check"](df, ctx).fillna(False).astype(bool)
        for idx in df.index[mask]:
            issues.append({"idx": idx, "rule": r["rule"], "severity": r["severity"],
                           "reason": r["reason"]})
            if r["severity"] == "error":
                error_idx.add(idx)

    kept = df.drop(index=sorted(error_idx))
    log = pd.DataFrame(
        [{"source_table": table,
          "record_key": "|".join(str(df.at[i["idx"], k]) for k in KEYS[table]),
          "rule": i["rule"], "severity": i["severity"], "reason": i["reason"],
          # keep the full raw record as JSON so it can be fixed and re-loaded later
          "raw_record": df.loc[i["idx"]].to_json(date_format="iso")}
         for i in issues],
        columns=["source_table", "record_key", "rule", "severity", "reason", "raw_record"],
    )
    return kept, log


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
    raw = {t: _read_staging(engine, t) for t in ORDER}
    ctx = {"raw": raw, "clean": {}}
    logs, run_rows = [], []

    for table in ORDER:
        kept, log = check_table(raw[table], table, ctx)
        ctx["clean"][table] = kept
        write_table(engine, kept, f"cln_{table}")
        logs.append(log)
        run_rows.append(
            {"run_id": run_id, "run_ts": run_ts, "source_table": table,
             "rows_in": len(raw[table]), "rows_passed": len(kept),
             "rows_quarantined": len(raw[table]) - len(kept),
             "warnings": int((log.severity == "warning").sum())})

    all_log = pd.concat(logs, ignore_index=True)
    all_log.insert(0, "run_id", run_id)
    write_table(engine, all_log, "dq_quarantine")
    # The run log is appended (history of runs), not replaced
    pd.DataFrame(run_rows).to_sql("dq_run_log", engine, if_exists="append", index=False)

    by_reason = all_log.groupby(["severity", "reason"]).size().sort_values(ascending=False)
    return {
        "run_id": run_id,
        "rows_in": int(sum(r["rows_in"] for r in run_rows)),
        "rows_passed": int(sum(r["rows_passed"] for r in run_rows)),
        "rows_quarantined": int(sum(r["rows_quarantined"] for r in run_rows)),
        "warnings": int(sum(r["warnings"] for r in run_rows)),
        "quarantine_by_table": {r["source_table"]: r["rows_quarantined"] for r in run_rows
                                if r["rows_quarantined"]},
        "issues_by_reason": {f"{sev}: {reason}": int(n) for (sev, reason), n in by_reason.items()},
    }


if __name__ == "__main__":
    from src.db import get_engine

    print(json.dumps(run_dq(get_engine()), indent=2))
