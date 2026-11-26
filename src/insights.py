"""Stage 6 - write reports/insights.md, a one-page consultant-style case-study report.

Every number is read from the KPI tables of this run, and the "which state / which category"
choices are made by the code (worst rank, highest rate), so the report can never drift away
from the data. The wording around the numbers is the consultant's judgement.
"""

from __future__ import annotations

import pandas as pd

from src.config import REPORTS_DIR, SOURCE_NOTICE


def _pct(x: float) -> str:
    return f"{x:.1%}"


def build_findings(k: dict[str, pd.DataFrame], metrics: dict) -> list[dict]:
    """Return 5 findings, each {title, evidence, recommendation}."""
    h = k["headline"].iloc[0]
    findings = []

    # 1) OTIF by state: worst ranked state vs. the best ranked one, and the transit time
    states = k["otif_by_state"].dropna(subset=["worst_otif_rank"]).sort_values("otif_rate")
    worst, best = states.iloc[0], states.iloc[-1]
    stages = k["lead_time_stages"].set_index("macro_region")
    region = stages.loc[worst.macro_region]
    findings.append({
        "title": f"Customers in {worst.state} ({worst.macro_region}) get the worst OTIF",
        "evidence": (
            f"OTIF in {worst.state} is {_pct(worst.otif_rate)} vs {_pct(best.otif_rate)} in "
            f"{best.state} (overall {_pct(h.otif_rate)}). Orders there take "
            f"{worst.avg_lead_time_days:.1f} days, of which {worst.avg_transit_days:.1f} are "
            f"carrier transit. Across the {worst.macro_region}, transit is "
            f"{_pct(region.transit_share)} of the lead time, while seller hand-off "
            f"(approval -> goods issue) takes only {region.avg_approval_to_gi_days:.1f} days."
        ),
        "recommendation": (
            f"The bottleneck is the carrier leg, not the warehouse: renegotiate carrier SLAs "
            f"for the {worst.macro_region}, test a regional carrier or a stock point in the "
            f"region, and keep the promised date (VDATU) realistic per state."
        ),
    })

    # 2) Late delivery drives complaints
    rv = k["review_vs_delivery"].set_index("delivery_outcome")
    late, on_time = rv.loc["late"], rv.loc["on time"]
    late_complaints = late.orders * late.low_review_rate
    complaint_share = late_complaints / (late_complaints + on_time.orders * on_time.low_review_rate)
    findings.append({
        "title": "A late delivery is the strongest predictor of a complaint",
        "evidence": (
            f"{_pct(late.low_review_rate)} of late orders get a 1-2 star review vs "
            f"{_pct(on_time.low_review_rate)} of on-time orders (average score "
            f"{late.avg_review_score:.2f} vs {on_time.avg_review_score:.2f}). Late orders are "
            f"only {_pct(late.share_of_orders)} of delivered, reviewed orders but cause "
            f"{_pct(complaint_share)} of their complaints."
        ),
        "recommendation": (
            "Treat OTIF as a customer-experience KPI: trigger a proactive message and a small "
            "voucher when an order passes its promised date, and report OTIF and complaint rate "
            "side by side."
        ),
    })

    # 3) Category with the most complaints (min. volume)
    cats = k["category_service"].dropna(subset=["complaint_rank"]).sort_values("complaint_rank")
    top = cats.iloc[0]
    uncategorized = cats[cats.category == "uncategorized"]
    extra = ""
    if not uncategorized.empty:
        u = uncategorized.iloc[0]
        extra = (f" Products with no category in the master data rank "
                 f"#{int(u.complaint_rank)} ({_pct(u.low_review_rate)}) - a data-quality "
                 f"issue that also hurts customers.")
    findings.append({
        "title": f"{top.category.replace('_', ' ').title()} has the highest complaint rate",
        "evidence": (
            f"{_pct(top.low_review_rate)} of {top.category} orders get a 1-2 star review "
            f"(company {_pct(h.low_review_rate)}), although its OTIF is {_pct(top.otif_rate)} "
            f"- so it is not only a delivery problem. Freight is {_pct(top.freight_to_price)} "
            f"of the item price.{extra}"
        ),
        "recommendation": (
            f"Investigate {top.category} complaints by seller and product (assembly, damage in "
            f"transit, description quality); there is no returns table in the source, so start "
            f"capturing return reasons (order reason AUGRU on return orders)."
        ),
    })

    # 4) Fashion & accessories segment (the case-study client's focus)
    seg = k["segment_summary"].set_index("segment")
    fa, other = seg.loc["Fashion & accessories"], seg.loc["Other"]
    findings.append({
        "title": "Fashion & accessories: small share, but better economics",
        "evidence": (
            f"The fashion segment is {_pct(fa.revenue_share)} of net revenue with an average "
            f"item price of BRL {fa.avg_item_price:.0f} (rest BRL {other.avg_item_price:.0f}). "
            f"Freight is {_pct(fa.freight_to_price)} of the price vs "
            f"{_pct(other.freight_to_price)}, complaints {_pct(fa.low_review_rate)} vs "
            f"{_pct(other.low_review_rate)}, OTIF {_pct(fa.otif_rate)} vs {_pct(other.otif_rate)}."
        ),
        "recommendation": (
            "For a fashion-retail roll-out, the segment is a good pilot: light parcels keep "
            "freight low. Focus the pilot on watches and bags (the top fashion sellers) and add "
            "size/fit return reasons before scaling clothing."
        ),
    })

    # 5) Cash side: payment approval by payment type
    pay = k["payment_types"].set_index("payment_type")
    card, boleto = pay.loc["credit_card"], pay.loc["boleto"]
    findings.append({
        "title": "Boleto payments slow down the start of fulfilment",
        "evidence": (
            f"Credit cards carry {_pct(card.amount_share)} of the paid value and are approved "
            f"after {card.avg_approval_hours:.1f} hours on average "
            f"({_pct(card.share_in_installments)} paid in instalments, "
            f"{card.avg_installments:.1f} on average). Boleto "
            f"({_pct(boleto.amount_share)} of value) takes {boleto.avg_approval_hours:.1f} hours "
            f"and {_pct(boleto.share_approved_after_24h)} need more than a day - the order "
            f"cannot ship before the payment is cleared."
        ),
        "recommendation": (
            "Nudge boleto customers to instant payment methods (e.g. PIX, launched in Brazil after "
            "this data period) and promise delivery dates from payment approval, not from "
            "purchase, for boleto orders."
        ),
    })
    return findings


def write_insights(k: dict[str, pd.DataFrame], metrics: dict) -> str:
    h = k["headline"].iloc[0]
    lines = [
        "# RetailLens - Order-to-Cash Insights (case study, real Olist data)",
        "",
        f"> {SOURCE_NOTICE}. Olist is a multi-category marketplace, not a fashion brand; the "
        "fashion & accessories segment is analysed separately for the case-study client. "
        "Generated by `src/insights.py` from the KPI tables of the latest pipeline run.",
        "",
        f"**Scope:** {metrics['headline']['sales_orders']:,} orders, "
        f"{metrics['headline']['order_items']:,} order items, "
        f"BRL {h.net_revenue / 1e6:.2f}M net revenue, orders placed "
        f"{metrics['analysis_window']['start']} to {metrics['analysis_window']['end']}. "
        f"**Headline:** OTIF {_pct(h.otif_rate)}, average lead time "
        f"{h.avg_lead_time_days:.1f} days (promised {h.avg_promised_days:.1f}), cancellation "
        f"rate {_pct(h.cancellation_rate)}, complaint rate {_pct(h.low_review_rate)}, payment "
        f"approval {h.avg_approval_hours:.1f} hours.",
        "",
    ]
    for i, f in enumerate(build_findings(k, metrics), start=1):
        lines += [
            f"## {i}. {f['title']}",
            f"**Evidence:** {f['evidence']}",
            "",
            f"**Recommendation:** {f['recommendation']}",
            "",
        ]
    lines += [
        "---",
        "*Method: SQL KPI queries in `sql/kpi/` over the star schema in `sql/0*.sql`; field "
        "mapping in `docs/sap_mapping.md`; definitions in `docs/data_dictionary.md`.*",
        "",
    ]
    text = "\n".join(lines)
    (REPORTS_DIR / "insights.md").write_text(text, encoding="utf-8")
    return text
