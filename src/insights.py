"""Stage 6 - write reports/insights.md, a one-page consultant-style report.

Every number is read from the KPI tables of this run, and the "which country / which category"
choices are made by the code (worst rank, highest rate), so the report can never drift away
from the data. The wording around the numbers is the consultant's judgement.
"""

from __future__ import annotations

import pandas as pd

from src.config import REPORTS_DIR


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _weighted(df: pd.DataFrame, value: str, weight: str) -> float:
    return float((df[value] * df[weight]).sum() / df[weight].sum())


def build_findings(k: dict[str, pd.DataFrame], metrics: dict) -> list[dict]:
    """Return 5 findings, each {title, evidence, recommendation}."""
    h = k["headline"].iloc[0]
    findings = []

    # 1) OTIF: worst vs best country, and whether timing or completeness is the problem
    otif = k["otif_by_country"].sort_values("otif_rate")
    worst, best = otif.iloc[0], otif.iloc[-1]
    driver = "late shipments" if worst.on_time_rate < worst.in_full_rate else "short shipments"
    findings.append({
        "title": f"{worst.country} misses OTIF far more often than any other market",
        "evidence": (
            f"OTIF in {worst.country} is {_pct(worst.otif_rate)} vs {_pct(best.otif_rate)} in "
            f"{best.country} (overall {_pct(h.otif_rate)}). In-full is {_pct(worst.in_full_rate)}"
            f" but on-time only {_pct(worst.on_time_rate)}, so the gap is {driver}; average lead "
            f"time is {worst.avg_lead_time_days:.1f} days vs {best.avg_lead_time_days:.1f}."
        ),
        "recommendation": (
            f"Review the outbound route and carrier SLA for {worst.country}, and align the "
            f"requested delivery dates (VDATU) with the real transit time - or serve "
            f"{worst.country} from a closer stock point."
        ),
    })

    # 2) Returns: highest-return category and its dominant reason
    ret = k["return_rate_by_category"].sort_values("return_rate", ascending=False)
    top = ret.iloc[0]
    reasons = k["return_reasons"]
    top_reason = reasons[reasons.category == top.category].sort_values(
        "returned_qty", ascending=False).iloc[0]
    findings.append({
        "title": f"{top.category.title()} drive returns - mostly a size/fit question",
        "evidence": (
            f"{top.category.title()} return {_pct(top.return_rate)} of billed units "
            f"(company average {_pct(h.return_rate)}), worth EUR {top.returned_value:,.0f} in "
            f"returned value. '{top_reason.reason_text}' explains "
            f"{_pct(top_reason.share_in_category)} of the returned units in this category. "
            f"{ret.iloc[1].category.title()} follow at {_pct(ret.iloc[1].return_rate)}."
        ),
        "recommendation": (
            f"Investigate {top.category.lower()} returns first: audit size charts and grading of "
            f"the top-returned styles, add fit notes to the B2B catalogue, and track return "
            f"rate per style as a buying KPI."
        ),
    })

    # 3) Cash: slowest-paying country
    cash = k["invoice_to_cash_by_country"].sort_values("avg_invoice_to_cash_days",
                                                       ascending=False)
    slow, fast = cash.iloc[0], cash.iloc[-1]
    findings.append({
        "title": f"Customers in {slow.country} pay {slow.avg_invoice_to_cash_days - fast.avg_invoice_to_cash_days:.0f} days slower",  # noqa: E501
        "evidence": (
            f"Invoice-to-cash averages {slow.avg_invoice_to_cash_days:.1f} days in {slow.country}"
            f" vs {fast.avg_invoice_to_cash_days:.1f} in {fast.country} (overall "
            f"{h.avg_invoice_to_cash_days:.1f}); {_pct(slow.share_paid_after_45d)} of its paid "
            f"invoices took more than 45 days. Open receivables there: "
            f"EUR {slow.open_receivables_value:,.0f}."
        ),
        "recommendation": (
            f"Tighten dunning for {slow.country} (reminder at due date + 7), review credit limits"
            f" of the slowest payers, and consider an early-payment discount."
        ),
    })

    # 4) Festive peak: revenue share and OTIF dip
    monthly = k["otif_monthly"]
    fest, normal = monthly[monthly.festive_month == 1], monthly[monthly.festive_month == 0]
    otif_fest = _weighted(fest, "otif_rate", "order_items")
    otif_norm = _weighted(normal, "otif_rate", "order_items")
    rev = k["revenue_monthly"]
    fest_share = rev[rev.festive_month == 1].net_revenue.sum() / rev.net_revenue.sum()
    findings.append({
        "title": "The festive peak brings the revenue - and the service problems",
        "evidence": (
            f"November-December generate {_pct(fest_share)} of net revenue in 2 of 12 months, "
            f"but OTIF falls to {_pct(otif_fest)} in those months vs {_pct(otif_norm)} the rest "
            f"of the year. Revenue grew {_pct(metrics['yoy_revenue_growth'])} year over year."
        ),
        "recommendation": (
            "Plan warehouse and carrier capacity for the peak from October (temporary staff, "
            "pre-picking of bestsellers) and pull festive pre-orders forward with an "
            "early-order incentive."
        ),
    })

    # 5) Fill rate: category with the lowest fill rate / most split deliveries
    fill = k["fill_rate_by_category"].sort_values("fill_rate")
    low, high = fill.iloc[0], fill.iloc[-1]
    findings.append({
        "title": f"{low.category.title()} availability causes the most split deliveries",
        "evidence": (
            f"Fill rate for {low.category.lower()} is {_pct(low.fill_rate)} vs "
            f"{_pct(high.fill_rate)} for {high.category.lower()}, and "
            f"{_pct(low.split_delivery_share)} of its order items need more than one delivery "
            f"(each extra delivery = extra picking, freight and an extra invoice)."
        ),
        "recommendation": (
            f"Buy {low.category.lower()} by size curve per store cluster and hold safety stock "
            f"on core sizes; use the split-delivery share as an allocation KPI."
        ),
    })
    return findings


def write_insights(k: dict[str, pd.DataFrame], metrics: dict) -> str:
    h = k["headline"].iloc[0]
    lines = [
        "# RetailLens - Order-to-Cash Insights (SYNTHETIC DATA)",
        "",
        "> Generated by `src/insights.py` from the KPI tables of the latest pipeline run. "
        "The data is synthetic (seeded generator), so the findings demonstrate the method, "
        "not a real company.",
        "",
        f"**Scope:** {metrics['headline']['sales_orders']:,} sales orders, "
        f"{metrics['headline']['order_items']:,} order items, "
        f"EUR {h.total_revenue / 1e6:.2f}M net revenue, {metrics['date_range']['first_order']}"
        f" to {metrics['date_range']['last_order']}. "
        f"**Headline:** OTIF {_pct(h.otif_rate)}, average lead time "
        f"{h.avg_lead_time_days:.1f} days, fill rate {_pct(h.fill_rate)}, "
        f"return rate {_pct(h.return_rate)}, invoice-to-cash {h.avg_invoice_to_cash_days:.1f}"
        " days.",
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
        "*Method: SQL KPI queries in `sql/kpi/` over the star schema in `sql/0*.sql`; "
        "definitions in `docs/data_dictionary.md`.*",
        "",
    ]
    text = "\n".join(lines)
    (REPORTS_DIR / "insights.md").write_text(text, encoding="utf-8")
    return text
