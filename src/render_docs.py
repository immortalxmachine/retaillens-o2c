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
    raw = m["source_row_counts"]
    w = m["analysis_window"]
    rows = [
        ("Source rows (9 Olist CSVs)", f"{sum(raw.values()):,}"),
        ("Orders / order items in analysis window",
         f"{h['sales_orders']:,} / {h['order_items']:,} ({w['start']} to {w['end']})"),
        ("Customers / sellers", f"{h['customers']:,} / {h['sellers']:,}"),
        ("Rows checked by DQ / quarantined / warnings",
         f"{dq['rows_in']:,} / {dq['rows_quarantined']:,} / {dq['warnings']:,}"),
        ("Net revenue (non-cancelled items)", f"BRL {h['net_revenue'] / 1e6:.2f}M"),
        (f"Revenue growth {m['yoy']['label']}", f"{m['yoy']['growth']:.1%}"),
        ("OTIF (on-time in-full)", f"{h['otif_rate']:.1%}"),
        ("Avg order-to-delivery lead time (promised)",
         f"{h['avg_lead_time_days']:.1f} days ({h['avg_promised_days']:.1f})"),
        ("Cancellation rate (items)", f"{h['cancellation_rate']:.2%}"),
        ("Complaint rate (review 1-2 stars)", f"{h['low_review_rate']:.1%}"),
        ("Avg purchase-to-payment-approval", f"{h['avg_approval_hours']:.1f} hours"),
        ("Fashion & accessories share of revenue", f"{h['fashion_revenue_share']:.1%}"),
    ]
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return (
        f"_From `metrics.json` (run on {m['database']}, {m['dataset']}) - real Olist data, "
        f"CC BY-NC-SA 4.0._\n\n| Metric | Value |\n|---|---|\n{body}"
    )


def resume_bullets(m: dict) -> str:
    h, dq = m["headline"], m["dq"]
    worst = next(s for s in m["kpis"]["otif_by_state"] if s["worst_otif_rank"] == 1)
    rv = {r["delivery_outcome"]: r for r in m["kpis"]["review_vs_delivery"]}
    bullets = [
        f"Mapped {h['sales_orders']:,} real Olist e-commerce orders into SAP S/4HANA SD tables "
        f"(VBAK/VBAP/LIKP/LIPS/BSAD) and a star schema of CDS-style SQL views.",
        f"Built data-quality gates over {dq['rows_in']:,} rows, quarantining "
        f"{dq['rows_quarantined']} inconsistent records and logging {dq['warnings']:,} "
        f"warnings with reasons.",
        f"Wrote SQL KPIs (CTEs, RANK, LAG): OTIF {h['otif_rate']:.1%}, lead time "
        f"{h['avg_lead_time_days']:.1f} days, payment approval "
        f"{h['avg_approval_hours']:.0f} hours, complaint rate {h['low_review_rate']:.1%}.",
        f"Showed late orders draw {rv['late']['low_review_rate']:.0%} complaints vs "
        f"{rv['on time']['low_review_rate']:.0%} on time and {worst['state']} has worst OTIF "
        f"({worst['otif_rate']:.0%}); built Streamlit dashboard and Power BI model.",
    ]
    lines = ["# Resume bullets - RetailLens", "",
             "_Numbers generated from `metrics.json` by `src/render_docs.py` (real Olist data, "
             "Kaggle, CC BY-NC-SA 4.0)._", ""]
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
