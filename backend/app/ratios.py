"""八个核心财务比率的计算。

这个文件不 import 任何数据库相关的东西 —— 进去是普通数字，出来是普通数字。
好处：可以脱离数据库单独测试，换掉数据库也不用改这里。
"""

# 每个比率算出来后要几位小数。比率本身是无量纲的小数（0.4622 = 46.22%），
# 在这一层只做四舍五入，不乘 100、不加百分号 —— 那是展示层的事。
PRECISION = 4


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    """安全除法：任何一边缺数据、或者分母为 0，都返回 None。

    为什么返回 None 而不是 0：
    "算不出来" 和 "算出来等于 0" 是两件完全不同的事。
    一家公司股东权益为 0（资不抵债的边缘）时 ROE 是无意义的，不是 0。
    返回 None，前端显示 "—"，不会误导人。
    """
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, PRECISION)


# ---------- 盈利能力 ----------


def gross_margin(revenue, cost_of_goods_sold):
    """毛利率 = (营收 - 销货成本) / 营收。每 1 块钱收入里，扣掉直接成本后剩多少。"""
    if revenue is None or cost_of_goods_sold is None:
        return None
    return _divide(revenue - cost_of_goods_sold, revenue)


def net_margin(revenue, net_income):
    """净利率 = 净利润 / 营收。每 1 块钱收入最后落到股东口袋里多少。"""
    return _divide(net_income, revenue)


def roe(net_income, total_equity):
    """ROE = 净利润 / 股东权益。股东每投入 1 块钱，一年赚回多少。"""
    return _divide(net_income, total_equity)


def roa(net_income, total_assets):
    """ROA = 净利润 / 总资产。全部资产（不分借的还是自己的）每 1 块钱赚多少。

    ROE 和 ROA 的差距来自杠杆：ROE = ROA × 权益乘数。
    ROE 高但 ROA 平平，说明利润是借钱撬出来的，不是经营效率高。
    """
    return _divide(net_income, total_assets)


# ---------- 流动性 ----------


def current_ratio(current_assets, current_liabilities):
    """流动比率 = 流动资产 / 流动负债。一年内要还的钱，有多少一年内能变现的资产顶着。"""
    return _divide(current_assets, current_liabilities)


def quick_ratio(current_assets, inventory, current_liabilities):
    """速动比率 = (流动资产 - 存货) / 流动负债。

    为什么要减掉存货：存货是流动资产里最难快速变现的一项 ——
    急着还债时打折甩卖，未必卖得掉，卖掉也未必值账面价。
    减掉它才是"真能马上拿出来的钱"。零售业存货占比大，这两个比率会差很远。
    """
    if current_assets is None or inventory is None:
        return None
    return _divide(current_assets - inventory, current_liabilities)


# ---------- 杠杆 / 偿债能力 ----------


def debt_to_assets(total_liabilities, total_assets):
    """资产负债率 = 总负债 / 总资产。公司的家当里有多大比例是借来的。"""
    return _divide(total_liabilities, total_assets)


def equity_multiplier(total_assets, total_equity):
    """权益乘数 = 总资产 / 股东权益。股东每 1 块钱撑起了多少资产，就是杠杆倍数。

    和资产负债率是同一件事的两种说法：权益乘数 = 1 / (1 - 资产负债率)。
    杜邦分析里用的是这个形式：ROE = 净利率 × 资产周转率 × 权益乘数。
    """
    return _divide(total_assets, total_equity)


# ---------- 一次算全部 ----------

# 展示用的中文名和格式，前端和这里共用一份，避免两边对不上
RATIO_LABELS = {
    "gross_margin": ("毛利率", "percent"),
    "net_margin": ("净利率", "percent"),
    "roe": ("ROE", "percent"),
    "roa": ("ROA", "percent"),
    "current_ratio": ("流动比率", "times"),
    "quick_ratio": ("速动比率", "times"),
    "debt_to_assets": ("资产负债率", "percent"),
    "equity_multiplier": ("权益乘数", "times"),
}


def calculate_all(f: dict) -> dict:
    """输入一年的财务数据（普通 dict），返回八个比率（普通 dict）。

    参数用 dict 而不是数据库对象，是为了让这个函数不依赖 SQLAlchemy。
    缺字段时 f.get() 返回 None，上面每个函数都能安全处理，不会崩。
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
