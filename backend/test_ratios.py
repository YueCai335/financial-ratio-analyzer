"""比率计算的测试。

用一组好心算的数字，手算结果写死在这里，跟函数输出对比。
这是整个项目里最该有测试的地方：比率算错了，图画得再漂亮也是错的，
而且错得很隐蔽 —— 图表照样能画出一条平滑的线。

跑：backend/.venv/bin/python -m pytest test_ratios.py -v
"""

import pytest

from app import health, ratios

# 一组刻意挑的整数，所有比率都能心算验证
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
    """ROE = ROA × 权益乘数。这是恒等式，不成立说明某个公式写错了。

    0.05 × 2.5 = 0.125 ✓
    """
    roe = ratios.roe(SAMPLE["net_income"], SAMPLE["total_equity"])
    roa = ratios.roa(SAMPLE["net_income"], SAMPLE["total_assets"])
    em = ratios.equity_multiplier(SAMPLE["total_assets"], SAMPLE["total_equity"])
    assert roe == pytest.approx(roa * em, rel=1e-6)


def test_leverage_identity():
    """权益乘数 = 1 / (1 - 资产负债率)。同样是恒等式。"""
    dta = ratios.debt_to_assets(SAMPLE["total_liabilities"], SAMPLE["total_assets"])
    em = ratios.equity_multiplier(SAMPLE["total_assets"], SAMPLE["total_equity"])
    assert em == pytest.approx(1 / (1 - dta), rel=1e-6)


# ---------- 边界情况：这些才是真正容易出 bug 的地方 ----------


def test_zero_denominator_returns_none():
    """分母为 0 时返回 None，不能崩，也不能返回 0。"""
    assert ratios.roe(100, 0) is None
    assert ratios.current_ratio(500, 0) is None
    assert ratios.gross_margin(0, 0) is None


def test_missing_data_returns_none():
    """缺数据时返回 None，代表'算不出来'。"""
    assert ratios.net_margin(None, 100) is None
    assert ratios.net_margin(1000, None) is None
    assert ratios.quick_ratio(500, None, 250) is None


def test_negative_equity():
    """股东权益为负（资不抵债）时 ROE 会是负数 —— 这在数学上算得出来，
    但解读时要小心：负 ROE 配负权益，数值上可能显示成"正的"，是陷阱。
    这里确认函数不会静默出错。
    """
    assert ratios.roe(100, -500) == -0.2


def test_calculate_all_handles_empty_dict():
    """完全没数据时，八个比率全是 None，不能抛异常。"""
    result = ratios.calculate_all({})
    assert len(result) == 8
    assert all(v is None for v in result.values())


def test_calculate_all_matches_labels():
    """calculate_all 返回的 key 必须和 RATIO_LABELS 完全对上，
    否则前端会显示不出名字。加个字段忘了加标签，这个测试会抓到。
    """
    assert set(ratios.calculate_all(SAMPLE)) == set(ratios.RATIO_LABELS)


# ---------- 健康度规则 ----------


def test_healthy_company_has_no_warnings():
    """样本数据流动比率 2.0、资产负债率 0.6，都在阈值内。"""
    assert health.check(ratios.calculate_all(SAMPLE)) == []


def test_low_current_ratio_triggers_warning():
    weak = {**SAMPLE, "current_assets": 200.0}  # 200/250 = 0.8 < 1.0
    warnings = health.check(ratios.calculate_all(weak))
    assert any(w["ratio"] == "current_ratio" for w in warnings)


def test_loss_making_company_triggers_warning():
    losing = {**SAMPLE, "net_income": -50.0}
    warnings = health.check(ratios.calculate_all(losing))
    assert any(w["ratio"] == "net_margin" for w in warnings)
