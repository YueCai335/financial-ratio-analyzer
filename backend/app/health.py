"""健康度提示：一组写死的、可解释的阈值规则。

刻意不用任何模型、不做预测。每条规则的阈值和触发理由写在一起，
任何一条提示都能追溯到具体是哪个数字越过了哪条线。

阈值是通用经验值，不分行业 —— 这是已知局限：
零售业流动比率常年低于 1（占用供应商账期是它的商业模式，不是危险信号），
软件业毛利率 70% 很正常，制造业 30% 就不错了。
严谨的判断应该跟同行业中位数比，而不是跟一个固定数字比，暂不在当前范围内。
"""

# (比率名, 方向, 阈值, 触发时的解释)
# 方向 "below" = 低于阈值时告警，"above" = 高于阈值时告警
RULES = [
    (
        "current_ratio",
        "below",
        1.0,
        "流动比率低于 1，一年内到期的负债超过一年内能变现的资产，短期偿债压力大",
    ),
    (
        "quick_ratio",
        "below",
        0.5,
        "速动比率低于 0.5，剔除存货后可动用的流动资产不足短期负债的一半",
    ),
    (
        "debt_to_assets",
        "above",
        0.7,
        "资产负债率高于 70%，资产大部分由负债支撑，利率上行或经营波动时缓冲很薄",
    ),
    (
        "net_margin",
        "below",
        0.0,
        "净利率为负，本年度亏损",
    ),
    (
        "gross_margin",
        "below",
        0.1,
        "毛利率低于 10%，扣掉直接成本后留下的空间很小，几乎没有降价余地",
    ),
]


def check(computed_ratios: dict) -> list[dict]:
    """输入算好的比率，返回触发的告警列表。没触发就是空列表。"""
    warnings = []
    for key, direction, threshold, reason in RULES:
        value = computed_ratios.get(key)
        if value is None:
            continue
        triggered = value < threshold if direction == "below" else value > threshold
        if triggered:
            warnings.append(
                {
                    "ratio": key,
                    "value": value,
                    "threshold": threshold,
                    "message": reason,
                }
            )
    return warnings
