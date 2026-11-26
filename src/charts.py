"""Stage 5b - static KPI charts (PNG) saved from code into reports/charts/.

Each chart answers one question, uses one colour for the series and a second colour only to
highlight the bar the insights report talks about.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # no window - render straight to file (works in CI too)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import REPORTS_DIR  # noqa: E402

BLUE = "#2a78d6"  # main series
ORANGE = "#eb6834"  # highlight (worst performer)
AQUA = "#1baf7a"  # third series in the stacked chart
INK, MUTED = "#0b0b0b", "#52514e"
SUBTITLE = "Case study on real Olist orders (Kaggle, CC BY-NC-SA 4.0) mapped to SAP SD"


def _style(ax, title: str, grid_axis: str = "x") -> None:
    ax.set_title(title, loc="left", fontsize=13, color=INK, pad=22)
    ax.text(0, 1.02, SUBTITLE, transform=ax.transAxes, fontsize=8, color=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis=grid_axis, color="#eeeeee", linewidth=0.8)
    ax.set_axisbelow(True)


def _hbar(df: pd.DataFrame, label: str, value: str, title: str, path, pct=True) -> None:
    """Horizontal bar chart, first row highlighted (inputs are sorted worst-first)."""
    df = df.iloc[::-1]  # matplotlib draws bottom-up -> reverse so the worst is on top
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=110)
    colors = [BLUE] * (len(df) - 1) + [ORANGE]
    ax.barh(df[label], df[value], color=colors, height=0.6)
    for y, v in enumerate(df[value]):
        ax.text(v, y, f"  {v:.1%}" if pct else f"  {v:.1f}", va="center", fontsize=9, color=INK)
    if pct:
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    _style(ax, title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def make_charts(kpis: dict[str, pd.DataFrame]) -> list[str]:
    out = REPORTS_DIR / "charts"
    out.mkdir(parents=True, exist_ok=True)
    files = []

    states = kpis["otif_by_state"].dropna(subset=["worst_otif_rank"])
    states = states.sort_values("worst_otif_rank").head(10)
    _hbar(states, "state", "otif_rate", "OTIF % - 10 worst customer states (min. 300 items)",
          out / "otif_by_state.png")
    files.append("otif_by_state.png")

    cats = kpis["category_service"].dropna(subset=["complaint_rank"])
    cats = cats.sort_values("complaint_rank").head(10)
    _hbar(cats, "category", "low_review_rate",
          "Complaint rate (review score 1-2) - top 10 categories",
          out / "complaints_by_category.png")
    files.append("complaints_by_category.png")

    rv = kpis["review_vs_delivery"].sort_values("low_review_rate", ascending=False)
    _hbar(rv, "delivery_outcome", "low_review_rate",
          "Complaint rate: late vs on-time deliveries", out / "complaints_late_vs_on_time.png")
    files.append("complaints_late_vs_on_time.png")

    # Stacked bars: where the order-to-delivery days go, per macro-region
    st = kpis["lead_time_stages"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=110)
    left = pd.Series(0.0, index=st.index)
    for col, name, color in [("avg_approval_days", "purchase -> payment approved", AQUA),
                             ("avg_approval_to_gi_days", "approved -> carrier hand-off", ORANGE),
                             ("avg_transit_days", "carrier transit -> customer", BLUE)]:
        ax.barh(st["macro_region"], st[col], left=left, color=color, height=0.6, label=name,
                edgecolor="white", linewidth=2)
        left = left + st[col]
    for y, v in enumerate(left):
        ax.text(v, y, f"  {v:.1f} d", va="center", fontsize=9, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _style(ax, "Order-to-delivery days by stage and macro-region")
    fig.tight_layout()
    fig.savefig(out / "lead_time_stages.png")
    plt.close(fig)
    files.append("lead_time_stages.png")

    # Monthly revenue line (single series -> the title names it)
    rev = kpis["revenue_monthly"]
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=110)
    ax.plot(rev["month_key"], rev["net_revenue"] / 1e6, color=BLUE, linewidth=2)
    festive = rev[rev["festive_month"] == 1]
    ax.scatter(festive["month_key"], festive["net_revenue"] / 1e6, color=ORANGE, s=40,
               zorder=3, label="Black Friday / Christmas months")
    ax.set_ylabel("Net revenue (BRL million)", color=MUTED, fontsize=9)
    ax.set_xticks(rev["month_key"][::3])
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _style(ax, "Monthly net revenue (non-cancelled item value)", grid_axis="y")
    fig.tight_layout()
    fig.savefig(out / "revenue_monthly.png")
    plt.close(fig)
    files.append("revenue_monthly.png")
    return files
