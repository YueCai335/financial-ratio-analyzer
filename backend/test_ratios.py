"""Tests for the ratio calculations.

A set of numbers chosen to be easy to check by hand, with the expected
results hard-coded here and compared against the function output. This is
the most important place in the project to have tests: a wrong ratio
formula produces a chart that still looks fine — a smooth, plausible line —
so the bug hides well without a test to catch it.

Run: backend/.venv/bin/python -m pytest test_ratios.py -v
"""

import pytest

from app import health, ratios

# A set of round numbers chosen so every ratio can be verified by mental math
SAMPLE = {
    "revenue": 1000.0,
    "cost_of_goods_sold": 600.0,
    "operating_income": 250.0,
    "net_income": 100.0,
    "total_assets": 2000.0,
    "total_liabilities": 1200.0,
    "total_equity": 800.0,
    "current_assets": 500.0,
    "current_liabilities": 250.0,
    "inventory": 100.0,
}


def test_gross_margin():
    # (1000 - 600) / 1000 = 0.4
    assert ratios.gross_margin(1000, 600) == 0.4


def test_net_margin():
    # 100 / 1000 = 0.1
    assert ratios.net_margin(1000, 100) == 0.1


def test_roe():
    # 100 / 800 = 0.125
    assert ratios.roe(100, 800) == 0.125


def test_roa():
    # 100 / 2000 = 0.05
    assert ratios.roa(100, 2000) == 0.05


def test_current_ratio():
    # 500 / 250 = 2.0
    assert ratios.current_ratio(500, 250) == 2.0


def test_quick_ratio():
    # (500 - 100) / 250 = 1.6
    assert ratios.quick_ratio(500, 100, 250) == 1.6


def test_debt_to_assets():
    # 1200 / 2000 = 0.6
    assert ratios.debt_to_assets(1200, 2000) == 0.6


def test_equity_multiplier():
    # 2000 / 800 = 2.5
    assert ratios.equity_multiplier(2000, 800) == 2.5


def test_dupont_identity():
    """ROE = ROA x equity multiplier. This is an identity — if it doesn't
    hold, some formula is wrong.

    0.05 x 2.5 = 0.125 (checks out)
    """
    roe = ratios.roe(SAMPLE["net_income"], SAMPLE["total_equity"])
    roa = ratios.roa(SAMPLE["net_income"], SAMPLE["total_assets"])
    em = ratios.equity_multiplier(SAMPLE["total_assets"], SAMPLE["total_equity"])
    assert roe == pytest.approx(roa * em, rel=1e-6)


def test_leverage_identity():
    """Equity multiplier = 1 / (1 - debt-to-assets). Also an identity."""
    dta = ratios.debt_to_assets(SAMPLE["total_liabilities"], SAMPLE["total_assets"])
    em = ratios.equity_multiplier(SAMPLE["total_assets"], SAMPLE["total_equity"])
    assert em == pytest.approx(1 / (1 - dta), rel=1e-6)


# ---------- Edge cases: where real bugs actually hide ----------


def test_zero_denominator_returns_none():
    """A zero denominator returns None — must not crash, and must not
    return 0.
    """
    assert ratios.roe(100, 0) is None
    assert ratios.current_ratio(500, 0) is None
    assert ratios.gross_margin(0, 0) is None


def test_missing_data_returns_none():
    """Missing data returns None, meaning 'cannot be computed'."""
    assert ratios.net_margin(None, 100) is None
    assert ratios.net_margin(1000, None) is None
    assert ratios.quick_ratio(500, None, 250) is None


def test_negative_equity():
    """Negative equity (insolvency) produces a negative ROE — mathematically
    fine, but a trap when reading the number: a negative ROE paired with
    negative equity can look "positive" at a glance. This test just confirms
    the function doesn't fail silently.
    """
    assert ratios.roe(100, -500) == -0.2


def test_calculate_all_handles_empty_dict():
    """With no data at all, all eight ratios are None — must not raise."""
    result = ratios.calculate_all({})
    assert len(result) == 8
    assert all(v is None for v in result.values())


def test_calculate_all_matches_labels():
    """The keys returned by calculate_all must exactly match RATIO_LABELS,
    or the frontend won't have a name to display. This test catches a field
    added without a matching label.
    """
    assert set(ratios.calculate_all(SAMPLE)) == set(ratios.RATIO_LABELS)


# ---------- Health check rules ----------


def test_healthy_company_has_no_warnings():
    """Sample data has a current ratio of 2.0 and debt-to-assets of 0.6,
    both within the thresholds.
    """
    assert health.check(ratios.calculate_all(SAMPLE)) == []


def test_low_current_ratio_triggers_warning():
    weak = {**SAMPLE, "current_assets": 200.0}  # 200/250 = 0.8 < 1.0
    warnings = health.check(ratios.calculate_all(weak))
    assert any(w["ratio"] == "current_ratio" for w in warnings)


def test_loss_making_company_triggers_warning():
    losing = {**SAMPLE, "net_income": -50.0}
    warnings = health.check(ratios.calculate_all(losing))
    assert any(w["ratio"] == "net_margin" for w in warnings)
