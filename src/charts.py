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
INK, MUTED = "#0b0b0b", "#52514e"
SUBTITLE = "SYNTHETIC DATA - RetailLens fashion wholesale, SAP SD structures"


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
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=110)
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

    _hbar(kpis["otif_by_country"], "country", "otif_rate",
          "OTIF % by customer country (worst highlighted)", out / "otif_by_country.png")
    files.append("otif_by_country.png")

    _hbar(kpis["return_rate_by_category"], "category", "return_rate",
          "Return rate % by category (highest highlighted)", out / "return_rate_by_category.png")
    files.append("return_rate_by_category.png")

    _hbar(kpis["invoice_to_cash_by_country"], "country", "avg_invoice_to_cash_days",
          "Average invoice-to-cash days by country", out / "invoice_to_cash_by_country.png",
          pct=False)
    files.append("invoice_to_cash_by_country.png")

    # Monthly revenue line (single series -> no legend needed, the title names it)
    rev = kpis["revenue_monthly"]
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=110)
    ax.plot(rev["month_key"], rev["net_revenue"] / 1e6, color=BLUE, linewidth=2)
    festive = rev[rev["festive_month"] == 1]
    ax.scatter(festive["month_key"], festive["net_revenue"] / 1e6, color=ORANGE, s=40,
               zorder=3, label="festive months (Nov-Dec)")
    ax.set_ylabel("Net revenue (EUR million)", color=MUTED, fontsize=9)
    ax.set_xticks(rev["month_key"][::3])
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _style(ax, "Monthly net revenue (billing date)", grid_axis="y")
    fig.tight_layout()
    fig.savefig(out / "revenue_monthly.png")
    plt.close(fig)
    files.append("revenue_monthly.png")
    return files
