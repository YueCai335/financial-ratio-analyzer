from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Company(Base):
    # 这张表在数据库里叫什么名字
    __tablename__ = "companies"

    # Mapped[int] = 这一列存整数
    # primary_key=True = 这是行号，自动 1,2,3... 递增，不用你填
    id: Mapped[int] = mapped_column(primary_key=True)

    # Mapped[str] = 存文字，不带 | None 就是必填（数据库层面 NOT NULL）
    # String(100) = 最长 100 个字符
    name: Mapped[str] = mapped_column(String(100))

    # Mapped[str | None] = 存文字，可以为空。"| None" 就是"允许没有"的意思
    ticker: Mapped[str | None] = mapped_column(String(10))
    industry: Mapped[str | None] = mapped_column(String(50))

    # 这一行不是数据库里的列，是给 Python 用的快捷方式：
    # 拿到一个 company 对象后，company.statements 直接就是它名下所有年份的财报
    statements: Mapped[list["FinancialStatement"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )


class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 外键：这条财报属于哪家公司。存的是 companies 表里的 id
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))

    fiscal_year: Mapped[int] = mapped_column()

    # ---- 利润表 ----
    # Float = 存小数。金额用 Float 有浮点误差（0.1+0.2 != 0.3），
    # 记账系统绝不能用，但这里只拿它算比率、画图，误差在小数点后十几位，
    # 不影响任何结论。取舍见 README。
    revenue: Mapped[float | None] = mapped_column(Float)
    cost_of_goods_sold: Mapped[float | None] = mapped_column(Float)
    operating_income: Mapped[float | None] = mapped_column(Float)
    net_income: Mapped[float | None] = mapped_column(Float)

    # ---- 资产负债表 ----
    total_assets: Mapped[float | None] = mapped_column(Float)
    total_liabilities: Mapped[float | None] = mapped_column(Float)
    total_equity: Mapped[float | None] = mapped_column(Float)
    current_assets: Mapped[float | None] = mapped_column(Float)
    current_liabilities: Mapped[float | None] = mapped_column(Float)
    inventory: Mapped[float | None] = mapped_column(Float)

    # 金额字段全部允许为空：从年报上抄数字时可能某项一时找不到，
    # 先存进去，别的比率照样能算。算不出来的显示 "—"，比整条录不进去好。

    # 反向的快捷方式：statement.company 直接拿到所属公司对象
    company: Mapped["Company"] = relationship(back_populates="statements")

    # 同一家公司同一个财年只能有一条记录 —— 在数据库层面强制，
    # 这样就算代码写错了重复插入，数据库自己会拦下来
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_company_year"),
    )
