"""往数据库里灌几家公司的财报数据，用于功能演示。

数据来源：各公司 10-K 年报（SEC EDGAR, sec.gov/edgar），
取 "Consolidated Statements of Operations" 和 "Consolidated Balance Sheets"。

⚠️ 这批数字尚未逐项复核，仅用于演示图表和计算逻辑，不要直接拿去做投资分析。

单位：百万美元。
各公司财年结束日期不同：苹果 9 月底，微软 6 月底，沃尔玛 1 月底。
所以同一个 fiscal_year 覆盖的时间段并不完全重合，横向比较时心里要有数。

选这三家是有意的对照组：
  微软   —— 软件，毛利率极高，现金厚
  苹果   —— 硬件，毛利率中等，但股东权益被巨额回购压得很低，ROE 高得吓人
  沃尔玛 —— 零售，毛利率低、存货重、流动比率常年小于 1
三种完全不同的商业模式，画在同一张图上对比才有意思。
"""

from app.database import Base, SessionLocal, engine
from app.models import Company, FinancialStatement

# 字段顺序：营收, 销货成本, 营业利润, 净利润,
#           总资产, 总负债, 股东权益, 流动资产, 流动负债, 存货
FIELDS = [
    "revenue",
    "cost_of_goods_sold",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "inventory",
]

DATA = [
    {
        "name": "Apple",
        "ticker": "AAPL",
        "industry": "消费电子",
        "years": {
            2024: [391035, 210352, 123216, 93736, 364980, 308030, 56950, 152987, 176392, 7286],
            2023: [383285, 214137, 114301, 96995, 352583, 290437, 62146, 143566, 145308, 6331],
            2022: [394328, 223546, 119437, 99803, 352755, 302083, 50672, 135405, 153982, 4946],
            2021: [365817, 212981, 108949, 94680, 351002, 287912, 63090, 134836, 125481, 6580],
            2020: [274515, 169559, 66288, 57411, 323888, 258549, 65339, 143713, 105392, 4061],
        },
    },
    {
        "name": "Microsoft",
        "ticker": "MSFT",
        "industry": "软件",
        "years": {
            2024: [245122, 74114, 109433, 88136, 512163, 243686, 268477, 159734, 125286, 1246],
            2023: [211915, 65863, 88523, 72361, 411976, 205753, 206223, 184257, 104149, 2500],
            2022: [198270, 62650, 83383, 72738, 364840, 198298, 166542, 169684, 95082, 3742],
            2021: [168088, 52232, 69916, 61271, 333779, 191791, 141988, 184406, 88657, 2636],
            2020: [143015, 46078, 52959, 44281, 301311, 183007, 118304, 181915, 72310, 1895],
        },
    },
    {
        "name": "Walmart",
        "ticker": "WMT",
        "industry": "零售",
        "years": {
            2024: [648125, 490142, 27012, 15511, 252399, 168455, 83944, 76877, 92415, 54892],
            2023: [611289, 463721, 20428, 11680, 243197, 160502, 82695, 75655, 92198, 56576],
            2022: [572754, 429000, 25942, 13673, 244860, 153943, 91891, 81070, 87379, 56511],
        },
    },
]


def main():
    # 先清空重建，让这个脚本可以反复运行而不会撞上唯一约束
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for entry in DATA:
            company = Company(
                name=entry["name"],
                ticker=entry["ticker"],
                industry=entry["industry"],
            )
            db.add(company)
            db.flush()  # flush 让数据库分配 id，但还不提交，这样下面能拿到 company.id

            for year, values in entry["years"].items():
                db.add(
                    FinancialStatement(
                        company_id=company.id,
                        fiscal_year=year,
                        **dict(zip(FIELDS, values)),
                    )
                )
            print(f"  {entry['name']:<12} {len(entry['years'])} 年")

        db.commit()
        print("\n数据已写入 backend/financials.db")
    finally:
        db.close()


if __name__ == "__main__":
    main()
