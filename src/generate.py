"""Seeded generator for a SYNTHETIC fashion-retail dataset in SAP S/4HANA SD table structures.

No public S/4HANA dataset exists, so we simulate one. Table and field names follow SAP
(KNA1, MARA, MAKT, VBAK, VBAP, LIKP, LIPS, VBRK, VBRP, BSAD) so the SQL reads like it would
on a real system. The business story: a European fashion wholesaler selling to a few hundred
retail stores (B2B), two years of orders, SS/AW seasons, festive peaks, partial and late
deliveries, returns that differ by category, and customers that pay on different schedules.

At the end we inject a small, documented set of data-quality issues (see DQ_INJECTION) so the
data-quality stage of the pipeline has real work to do.

Run:  python -m src.generate          (writes CSVs to data/raw/)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RAW_DIR, SEED

# ---------------------------------------------------------------------------
# Business parameters (all synthetic, chosen to look plausible)
# ---------------------------------------------------------------------------
START = pd.Timestamp("2023-01-01")  # first order date
END = pd.Timestamp("2024-12-31")  # last order date
EXTRACT_DATE = pd.Timestamp("2025-02-15")  # "today" of the extract: later events don't exist yet

# Country -> (regions REGIO, share of customers, extra delivery days, extra payment days)
COUNTRIES = {
    "DE": (["BY", "BW", "NW", "BE", "HH"], 0.30, 0, 0),
    "FR": (["IDF", "ARA", "PAC", "NAQ"], 0.22, 1, 3),
    "IT": (["LOM", "LAZ", "CAM", "PIE"], 0.18, 3, 9),
    "ES": (["MD", "CT", "AN", "VC"], 0.15, 2, 6),
    "NL": (["NH", "ZH", "UT"], 0.15, 0, 1),
}

# Category MATKL -> (base unit price EUR, return probability per billed line, assortment share)
CATEGORIES = {
    "TOPS": (19.0, 0.06, 0.18),
    "DRESSES": (49.0, 0.20, 0.12),
    "DENIM": (45.0, 0.11, 0.12),
    "KNITWEAR": (39.0, 0.07, 0.12),
    "OUTERWEAR": (89.0, 0.08, 0.10),
    "FOOTWEAR": (69.0, 0.16, 0.12),
    "ACCESSORIES": (15.0, 0.03, 0.14),
    "ACTIVEWEAR": (29.0, 0.05, 0.10),
}

COLORS = ["Black", "White", "Navy", "Olive", "Sand", "Burgundy", "Grey", "Ecru", "Rust", "Sky"]
STYLES = ["Classic", "Relaxed", "Slim", "Oversized", "Cropped", "Essential", "Premium", "Vintage"]
NOUNS = {
    "TOPS": ["T-Shirt", "Blouse", "Shirt", "Tank Top"],
    "DRESSES": ["Midi Dress", "Maxi Dress", "Shirt Dress", "Wrap Dress"],
    "DENIM": ["Straight Jeans", "Skinny Jeans", "Denim Jacket", "Denim Skirt"],
    "KNITWEAR": ["Cardigan", "Crew Sweater", "Turtleneck", "Knit Vest"],
    "OUTERWEAR": ["Trench Coat", "Puffer Jacket", "Wool Coat", "Parka"],
    "FOOTWEAR": ["Sneaker", "Ankle Boot", "Loafer", "Sandal"],
    "ACCESSORIES": ["Scarf", "Belt", "Tote Bag", "Cap"],
    "ACTIVEWEAR": ["Leggings", "Sports Bra", "Track Jacket", "Running Shorts"],
}
STORE_WORDS = ["Moda", "Stil", "Urban", "Nord", "Bella", "Chic", "Atelier", "Linea", "Trend",
               "Loft"]
LEGAL_FORM = {"DE": "GmbH", "FR": "SARL", "IT": "S.r.l.", "ES": "S.L.", "NL": "B.V."}

# Size-curve categories run out of single sizes more often -> more partial / short deliveries
STOCKOUT_FACTOR = {"FOOTWEAR": 2.2, "DENIM": 1.6}

# Return reasons (SAP order reason AUGRU on a return order)
RETURN_REASONS = {"R01": "Size / fit", "R02": "Quality defect", "R03": "Not as described"}
LATE_REASON = "R04"  # "Delivered too late" - used when the original delivery was late

# Documented data-quality issues injected on purpose (counts are exact)
DQ_INJECTION = {
    "vbak_missing_erdat": 12,  # sales order header without creation date
    "vbap_negative_kwmeng": 25,  # order item with negative quantity
    "vbap_orphan_items": 20,  # order item whose VBELN has no VBAK header
    "likp_missing_wadat_ist": 10,  # delivery header without actual goods-issue date
    "lips_orphan_items": 15,  # delivery item whose VBELN has no LIKP header
}


def _seasonal_multiplier(day: pd.Timestamp) -> float:
    """Relative order intensity for one calendar day (B2B fashion pattern)."""
    m, d = day.month, day.day
    mult = 1.0
    if (m == 11 and d >= 10) or (m == 12 and d <= 20):
        mult = 2.2  # Black Friday / Christmas pre-orders - the festive peak
    elif m in (3, 9):
        mult = 1.35  # SS launch (March) and AW launch (September)
    elif m in (1, 7):
        mult = 1.15  # end-of-season sales
    elif m == 8:
        mult = 0.8  # summer lull
    if day.day_of_week >= 5:
        mult *= 0.5  # stores order less on weekends
    return mult


def _make_customers(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """KNA1 - customer master. Also returns hidden behaviour columns (prefixed with x_)."""
    codes = list(COUNTRIES)
    shares = np.array([COUNTRIES[c][1] for c in codes])
    land1 = rng.choice(codes, size=n, p=shares / shares.sum())
    rows = []
    for i, country in enumerate(land1):
        regions = COUNTRIES[country][0]
        name = f"{rng.choice(STORE_WORDS)} {rng.choice(STORE_WORDS)} {LEGAL_FORM[country]}"
        rows.append(
            {
                "KUNNR": f"{100001 + i:010d}",  # SAP customer numbers are 10-digit, zero padded
                "NAME1": name,
                "LAND1": country,
                "REGIO": rng.choice(regions),
                # hidden behaviour (not exported): order frequency and payment habit
                "x_weight": rng.lognormal(0, 0.8),
                "x_pay_delay": rng.normal(0, 6) + COUNTRIES[country][3],
                "x_terms": int(rng.choice([30, 60], p=[0.8, 0.2])),
                "x_plan_lead": int(rng.choice([5, 7, 10], p=[0.3, 0.5, 0.2])),
            }
        )
    return pd.DataFrame(rows)


def _make_materials(rng: np.random.Generator, n: int) -> pd.DataFrame:
    """MARA + MAKT - material master and description. Hidden list price + popularity."""
    cats = list(CATEGORIES)
    shares = np.array([CATEGORIES[c][2] for c in cats])
    matkl = rng.choice(cats, size=n, p=shares / shares.sum())
    rows = []
    for i, cat in enumerate(matkl):
        # Outerwear/knitwear are mostly AW, dresses/activewear mostly SS, rest mixed
        if cat in ("OUTERWEAR", "KNITWEAR"):
            p = [0.10, 0.70, 0.20]
        elif cat in ("DRESSES", "ACTIVEWEAR"):
            p = [0.65, 0.15, 0.20]
        else:
            p = [0.35, 0.35, 0.30]
        rows.append(
            {
                "MATNR": f"F{1000001 + i}",
                "MATKL": cat,  # material group = product category
                "SAISO": rng.choice(["SS", "AW", "CORE"], p=p),  # season (SAP Fashion field)
                "MAKTX": f"{rng.choice(STYLES)} {rng.choice(COLORS)} {rng.choice(NOUNS[cat])}",
                "x_price": round(CATEGORIES[cat][0] * rng.lognormal(0, 0.25), 2),
                "x_popularity": rng.pareto(1.5) + 0.05,  # a few bestsellers, a long tail
            }
        )
    return pd.DataFrame(rows)


def generate(seed: int = SEED, scale: float = 1.0) -> dict[str, pd.DataFrame]:
    """Build every SAP table as a pandas DataFrame.

    seed  - same seed => byte-identical output (tested in tests/test_generate.py)
    scale - shrink for fast tests (e.g. 0.05), 1.0 for the full dataset
    """
    rng = np.random.default_rng(seed)
    customers = _make_customers(rng, max(20, int(400 * scale)))
    materials = _make_materials(rng, max(40, int(1500 * scale)))

    # Materials grouped by season so order months can prefer the right collection
    # (plain Python records + probability arrays are much faster than DataFrame.iloc in a loop)
    pools = {}
    for s in ("SS", "AW", "CORE"):
        pool = materials[materials.SAISO == s]
        if pool.empty:
            pool = materials
        pools[s] = (list(pool.itertuples()), (pool.x_popularity / pool.x_popularity.sum()).values)
    cust_records = list(customers.itertuples())
    cust_p = (customers.x_weight / customers.x_weight.sum()).values

    vbak, vbap, likp, lips, vbrk, vbrp, bsad, returns = ([] for _ in range(8))
    order_no, deliv_no, bill_no, ret_no, pay_no = 100000, 80000000, 90000000, 60000000, 1400000000

    base_orders_per_day = 15.0 * scale
    for day in pd.date_range(START, END, freq="D"):
        growth = 1 + 0.12 * (day - START).days / 365  # ~12% year-over-year growth
        n_orders = rng.poisson(base_orders_per_day * growth * _seasonal_multiplier(day))
        ss_months = 2 <= day.month <= 7
        festive = (day.month == 11 and day.day >= 10) or day.month == 12
        sale_month = day.month in (1, 7)

        for _ in range(n_orders):
            order_no += 1
            vbeln = f"{order_no:010d}"
            c = cust_records[rng.choice(len(cust_records), p=cust_p)]
            vdatu = day + pd.Timedelta(days=c.x_plan_lead)  # requested delivery date

            # ---- VBAP: order items -------------------------------------------------
            n_items = min(8, 1 + rng.poisson(1.6))
            season_p = [0.6, 0.1, 0.3] if ss_months else [0.1, 0.6, 0.3]
            items = []
            for k in range(n_items):
                records, probs = pools[rng.choice(["SS", "AW", "CORE"], p=season_p)]
                m = records[rng.choice(len(records), p=probs)]
                qty = int(1 + rng.negative_binomial(3, 0.2))  # mean ~13 units per line
                discount = rng.uniform(0.10, 0.30) if sale_month else rng.uniform(0, 0.10)
                unit = round(m.x_price * (1 - discount), 2)
                items.append((10 * (k + 1), m.MATNR, m.MATKL, qty, unit))
                vbap.append(
                    {"VBELN": vbeln, "POSNR": 10 * (k + 1), "MATNR": m.MATNR, "KWMENG": qty,
                     "VRKME": "PC", "NETWR": round(qty * unit, 2), "WAERK": "EUR"}
                )
            vbak.append(
                {"VBELN": vbeln, "AUART": "OR", "ERDAT": day, "VDATU": vdatu, "KUNNR": c.KUNNR,
                 "VKORG": "1000", "NETWR": round(sum(q * u for *_, q, u in items), 2),
                 "WAERK": "EUR"}
            )

            # ---- LIKP/LIPS: deliveries (main shipment + optional backorder) --------------
            country_delay = COUNTRIES[c.LAND1][2]
            lead = 1 + rng.gamma(2.0, 1.2) + country_delay + (2 if festive else 0)
            gi_main = day + pd.Timedelta(days=int(round(lead)))
            backorder = []  # (order item, material, qty, unit)
            shipments = [(gi_main, [])]
            for posnr, matnr, matkl, qty, unit in items:
                r = rng.random() / STOCKOUT_FACTOR.get(matkl, 1.0)
                if r < 0.06 and qty > 1:  # partial: ~60% now, rest in a backorder delivery
                    first = max(1, int(qty * rng.uniform(0.4, 0.8)))
                    shipments[0][1].append((posnr, matnr, matkl, first, unit))
                    backorder.append((posnr, matnr, matkl, qty - first, unit))
                elif r < 0.085 and qty > 1:  # short shipment: rest never delivered
                    shipments[0][1].append((posnr, matnr, matkl, max(1, int(qty * 0.7)), unit))
                else:
                    shipments[0][1].append((posnr, matnr, matkl, qty, unit))
            if backorder:
                shipments.append((gi_main + pd.Timedelta(days=int(rng.integers(5, 15))), backorder))

            for gi_date, ship_items in shipments:
                if gi_date > EXTRACT_DATE:
                    continue  # not shipped yet at extract time
                deliv_no += 1
                dvbeln = f"{deliv_no:010d}"
                late = gi_date > vdatu
                likp.append({"VBELN": dvbeln, "ERDAT": gi_date - pd.Timedelta(days=1),
                             "KUNNR": c.KUNNR, "LFDAT": vdatu, "WADAT_IST": gi_date})
                # ---- VBRK/VBRP: one invoice per delivery, billed 0-1 days after goods issue
                bill_no += 1
                bvbeln = f"{bill_no:010d}"
                fkdat = gi_date + pd.Timedelta(days=int(rng.integers(0, 2)))
                bill_total = 0.0
                for j, (posnr, matnr, matkl, qty, unit) in enumerate(ship_items, start=1):
                    lips.append({"VBELN": dvbeln, "POSNR": 10 * j, "MATNR": matnr, "LFIMG": qty,
                                 "VGBEL": vbeln, "VGPOS": posnr})
                    value = round(qty * unit, 2)
                    bill_total += value
                    vbrp.append({"VBELN": bvbeln, "POSNR": 10 * j, "MATNR": matnr, "FKIMG": qty,
                                 "NETWR": value, "VGBEL": dvbeln, "VGPOS": 10 * j,
                                 "AUBEL": vbeln, "AUPOS": posnr})
                    # ---- returns: probability by category, higher if delivery was late
                    p_ret = CATEGORIES[matkl][1] + (0.05 if late else 0)
                    if rng.random() < p_ret:
                        ret_date = fkdat + pd.Timedelta(days=int(rng.integers(7, 40)))
                        if ret_date <= EXTRACT_DATE:
                            ret_no += 1
                            rqty = max(1, int(np.ceil(qty * rng.uniform(0.2, 0.6))))
                            reason = (LATE_REASON if late and rng.random() < 0.5
                                      else rng.choice(list(RETURN_REASONS), p=[0.55, 0.25, 0.20]))
                            returns.append({"VBELN": f"{ret_no:010d}", "POSNR": 10, "AUART": "RE",
                                            "ERDAT": ret_date, "KUNNR": c.KUNNR, "MATNR": matnr,
                                            "KWMENG": rqty, "NETWR": round(rqty * unit, 2),
                                            "AUGRU": reason, "VGBEL": bvbeln, "VGPOS": 10 * j})
                vbrk.append({"VBELN": bvbeln, "FKART": "F2", "FKDAT": fkdat, "KUNAG": c.KUNNR,
                             "NETWR": round(bill_total, 2), "WAERK": "EUR"})

                # ---- BSAD: cleared customer item (payment) -------------------------------
                due = fkdat + pd.Timedelta(days=c.x_terms)
                augdt = due + pd.Timedelta(days=int(round(rng.normal(c.x_pay_delay, 5))))
                augdt = max(augdt, fkdat + pd.Timedelta(days=1))
                if rng.random() > 0.02 and augdt <= EXTRACT_DATE:  # ~2% never paid / still open
                    pay_no += 1
                    bsad.append({"BELNR": f"{pay_no:010d}", "KUNNR": c.KUNNR, "VBELN": bvbeln,
                                 "AUGDT": augdt, "DMBTR": round(bill_total, 2), "WAERS": "EUR"})

    tables = {
        "kna1": customers[["KUNNR", "NAME1", "LAND1", "REGIO"]],
        "mara": materials[["MATNR", "MATKL", "SAISO"]].assign(MTART="FERT"),
        "makt": materials[["MATNR", "MAKTX"]].assign(SPRAS="E"),
        "vbak": pd.DataFrame(vbak),
        "vbap": pd.DataFrame(vbap),
        "likp": pd.DataFrame(likp),
        "lips": pd.DataFrame(lips),
        "vbrk": pd.DataFrame(vbrk),
        "vbrp": pd.DataFrame(vbrp),
        "bsad": pd.DataFrame(bsad),
        "returns": pd.DataFrame(returns),
    }
    return inject_dq_issues(tables, rng)


def inject_dq_issues(tables: dict[str, pd.DataFrame], rng: np.random.Generator):
    """Plant the documented DQ issues (DQ_INJECTION) so the DQ stage can catch them."""
    t = {k: v.copy() for k, v in tables.items()}
    n = DQ_INJECTION

    # 1) VBAK: missing creation date ERDAT
    idx = rng.choice(t["vbak"].index, size=n["vbak_missing_erdat"], replace=False)
    t["vbak"]["ERDAT"] = t["vbak"]["ERDAT"].astype("object")
    t["vbak"].loc[idx, "ERDAT"] = None

    # 2) VBAP: negative order quantity (sign error from an interface)
    idx = rng.choice(t["vbap"].index, size=n["vbap_negative_kwmeng"], replace=False)
    t["vbap"].loc[idx, "KWMENG"] = -t["vbap"].loc[idx, "KWMENG"]

    # 3) VBAP: orphan items pointing to order numbers that do not exist in VBAK
    orphans = t["vbap"].sample(n["vbap_orphan_items"], random_state=int(rng.integers(1e9))).copy()
    orphans["VBELN"] = [f"{9900000 + i:010d}" for i in range(len(orphans))]
    t["vbap"] = pd.concat([t["vbap"], orphans], ignore_index=True)

    # 4) LIKP: missing actual goods-issue date
    idx = rng.choice(t["likp"].index, size=n["likp_missing_wadat_ist"], replace=False)
    t["likp"]["WADAT_IST"] = t["likp"]["WADAT_IST"].astype("object")
    t["likp"].loc[idx, "WADAT_IST"] = None

    # 5) LIPS: orphan delivery items pointing to deliveries that do not exist in LIKP
    orphans = t["lips"].sample(n["lips_orphan_items"], random_state=int(rng.integers(1e9))).copy()
    orphans["VBELN"] = [f"{89900000 + i:010d}" for i in range(len(orphans))]
    t["lips"] = pd.concat([t["lips"], orphans], ignore_index=True)
    return t


def write_csv(tables: dict[str, pd.DataFrame], out_dir: Path = RAW_DIR) -> None:
    """Write one CSV per SAP table plus a JSON note of the injected DQ issues."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    (out_dir / "_dq_injected.json").write_text(json.dumps(DQ_INJECTION, indent=2))


if __name__ == "__main__":
    data = generate()
    write_csv(data)
    for name, df in data.items():
        print(f"{name:8s} {len(df):>7,d} rows")
