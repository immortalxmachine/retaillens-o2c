"""Write the numbers from metrics.json into README.md and RESUME_BULLETS.md.

Nothing in those documents is typed by hand: README has a block between
<!-- METRICS:START --> and <!-- METRICS:END --> that this script replaces, and
RESUME_BULLETS.md is rewritten completely.

Run on its own:  python -m src.render_docs
"""

from __future__ import annotations

import json
import re

from src.config import METRICS_PATH, ROOT

START, END = "<!-- METRICS:START -->", "<!-- METRICS:END -->"


def metrics_table(m: dict) -> str:
    h, dq = m["headline"], m["dq"]
    raw = m["raw_row_counts"]
    rows = [
        ("Customers (KNA1)", f"{raw['kna1']:,}"),
        ("Materials (MARA)", f"{raw['mara']:,}"),
        ("Sales orders / order items (clean)", f"{h['sales_orders']:,} / {h['order_items']:,}"),
        ("Delivery items (LIPS) / billing items (VBRP)",
         f"{raw['lips']:,} / {raw['vbrp']:,}"),
        ("Rows checked by DQ / quarantined", f"{dq['rows_in']:,} / {dq['rows_quarantined']:,}"),
        ("Net revenue", f"EUR {h['total_revenue'] / 1e6:.2f}M"),
        ("Revenue growth 2024 vs 2023", f"{m['yoy_revenue_growth']:.1%}"),
        ("OTIF (on-time in-full)", f"{h['otif_rate']:.1%}"),
        ("Avg order-to-delivery lead time", f"{h['avg_lead_time_days']:.1f} days"),
        ("Fill rate", f"{h['fill_rate']:.1%}"),
        ("Return rate (units)", f"{h['return_rate']:.1%}"),
        ("Avg invoice-to-cash", f"{h['avg_invoice_to_cash_days']:.1f} days"),
    ]
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return (
        f"_From `metrics.json` (run on {m['database']}, seed {m['seed']}) - SYNTHETIC DATA._\n\n"
        f"| Metric | Value |\n|---|---|\n{body}"
    )


def resume_bullets(m: dict) -> str:
    h, dq = m["headline"], m["dq"]
    worst = m["kpis"]["otif_by_country"][0]
    top_ret = m["kpis"]["return_rate_by_category"][0]
    bullets = [
        f"Built SAP S/4HANA order-to-cash analytics on {h['order_items']:,} synthetic SD order "
        f"items (VBAK/VBAP/LIKP/VBRK) with a star schema of CDS-style SQL views on PostgreSQL.",
        f"Engineered data-quality gates checking {dq['rows_in']:,} rows for referential "
        f"integrity, mandatory fields and negatives, quarantining {dq['rows_quarantined']} with "
        f"reasons.",
        f"Wrote SQL KPIs (CTEs, RANK, LAG) for OTIF {h['otif_rate']:.1%}, lead time "
        f"{h['avg_lead_time_days']:.1f} days, invoice-to-cash "
        f"{h['avg_invoice_to_cash_days']:.0f} days, fill and return rates.",
        f"Built Streamlit dashboard, Power BI DAX model and consultant insights: "
        f"{worst['country']} OTIF "
        f"{worst['otif_rate']:.0%}, {top_ret['category'].lower()} returns "
        f"{top_ret['return_rate']:.1%}, with recommendations.",
    ]
    lines = ["# Resume bullets - RetailLens", "",
             "_Numbers generated from `metrics.json` by `src/render_docs.py` "
             "(dataset is SYNTHETIC)._", ""]
    lines += [f"- {b}" for b in bullets]
    for b in bullets:  # guard the <=25 words rule
        assert len(b.split()) <= 25, f"bullet too long ({len(b.split())} words): {b}"
    return "\n".join(lines) + "\n"


def render(m: dict | None = None) -> None:
    m = m or json.loads(METRICS_PATH.read_text())
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        block = f"{START}\n{metrics_table(m)}\n{END}"
        text = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, text,
                      flags=re.S)
        readme.write_text(text, encoding="utf-8")
    (ROOT / "RESUME_BULLETS.md").write_text(resume_bullets(m), encoding="utf-8")


if __name__ == "__main__":
    render()
