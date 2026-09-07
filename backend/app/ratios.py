"""Calculation of the eight core financial ratios.

This file imports nothing database-related — plain numbers go in, plain
numbers come out. Benefit: it can be tested in isolation from the database,
and swapping the database later requires no changes here.
"""

# Decimal places to round each ratio to. Ratios are dimensionless fractions
# (0.4622 = 46.22%); rounding happens at this layer only — multiplying by 100
# or adding a "%" sign is the presentation layer's job.
PRECISION = 4


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division: returns None if either side is missing, or the
    denominator is 0.

    Why None instead of 0:
    "cannot be computed" and "computes to zero" are two different things.
    When a company's equity is 0 (on the edge of insolvency), ROE is
    meaningless, not zero. Returning None lets the frontend show "—" instead
    of a misleading number.
    """
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, PRECISION)


# ---------- Profitability ----------


def gross_margin(revenue, cost_of_goods_sold):
    """Gross margin = (revenue - cost of goods sold) / revenue.
    How much of each dollar of revenue is left after direct costs.
    """
    if revenue is None or cost_of_goods_sold is None:
        return None
    return _divide(revenue - cost_of_goods_sold, revenue)


def net_margin(revenue, net_income):
    """Net margin = net income / revenue.
    How much of each dollar of revenue ultimately reaches shareholders.
    """
    return _divide(net_income, revenue)


def roe(net_income, total_equity):
    """ROE = net income / total equity.
    Return earned per dollar shareholders have invested.
    """
    return _divide(net_income, total_equity)


def roa(net_income, total_assets):
    """ROA = net income / total assets.
    Return earned per dollar of assets, regardless of how they were financed.

    The gap between ROE and ROA comes from leverage: ROE = ROA x equity
    multiplier. A high ROE with a flat ROA means the return is driven by
    borrowed money, not operating efficiency.
    """
    return _divide(net_income, total_assets)


# ---------- Liquidity ----------


def current_ratio(current_assets, current_liabilities):
    """Current ratio = current assets / current liabilities.
    How much liquidatable-within-a-year asset backs each dollar of debt due
    within a year.
    """
    return _divide(current_assets, current_liabilities)


def quick_ratio(current_assets, inventory, current_liabilities):
    """Quick ratio = (current assets - inventory) / current liabilities.

    Why inventory is subtracted: inventory is the hardest current asset to
    convert to cash quickly — a fire sale to cover debt may not clear it at
    book value, or at all. Removing it leaves "cash you can truly raise
    right now." Retailers carry heavy inventory, so this ratio and the
    current ratio can diverge sharply for them.
    """
    if current_assets is None or inventory is None:
        return None
    return _divide(current_assets - inventory, current_liabilities)


# ---------- Leverage / solvency ----------


def debt_to_assets(total_liabilities, total_assets):
    """Debt-to-assets = total liabilities / total assets.
    What fraction of the company's assets are funded by debt.
    """
    return _divide(total_liabilities, total_assets)


def equity_multiplier(total_assets, total_equity):
    """Equity multiplier = total assets / total equity.
    How many dollars of assets each dollar of equity supports — the leverage
    multiple.

    Equivalent to debt-to-assets from another angle:
    equity multiplier = 1 / (1 - debt-to-assets). This is the form used in
    DuPont analysis: ROE = net margin x asset turnover x equity multiplier.
    """
    return _divide(total_assets, total_equity)


# ---------- Compute everything at once ----------

# Display labels and formats, shared between backend and frontend so they
# never fall out of sync.
RATIO_LABELS = {
    "gross_margin": ("Gross Margin", "percent"),
    "net_margin": ("Net Margin", "percent"),
    "roe": ("ROE", "percent"),
    "roa": ("ROA", "percent"),
    "current_ratio": ("Current Ratio", "times"),
    "quick_ratio": ("Quick Ratio", "times"),
    "debt_to_assets": ("Debt to Assets", "percent"),
    "equity_multiplier": ("Equity Multiplier", "times"),
}


def calculate_all(f: dict) -> dict:
    """Takes one year of financial data (a plain dict) and returns the eight
    ratios (a plain dict).

    The parameter is a dict rather than a database object so this function
    stays independent of SQLAlchemy. f.get() returns None for missing
    fields, which every function above already handles safely.
    """
    return {
        "gross_margin": gross_margin(f.get("revenue"), f.get("cost_of_goods_sold")),
        "net_margin": net_margin(f.get("revenue"), f.get("net_income")),
        "roe": roe(f.get("net_income"), f.get("total_equity")),
        "roa": roa(f.get("net_income"), f.get("total_assets")),
        "current_ratio": current_ratio(
            f.get("current_assets"), f.get("current_liabilities")
        ),
        "quick_ratio": quick_ratio(
            f.get("current_assets"), f.get("inventory"), f.get("current_liabilities")
        ),
        "debt_to_assets": debt_to_assets(
            f.get("total_liabilities"), f.get("total_assets")
        ),
        "equity_multiplier": equity_multiplier(
            f.get("total_assets"), f.get("total_equity")
        ),
    }
