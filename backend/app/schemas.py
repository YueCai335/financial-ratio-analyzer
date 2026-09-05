"""Pydantic 模型：定义 API 的输入长什么样、输出长什么样。

和 models.py 的区别常让人困惑：
  models.py  = 数据库里怎么存（SQLAlchemy）
  schemas.py = 网络上怎么传（Pydantic）
分开的好处是数据库多存的字段不会不小心暴露给前端，
前端传来的垃圾数据也会在进数据库之前被 Pydantic 挡下来。
"""

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    ticker: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=50)


class CompanyOut(BaseModel):
    # 允许直接从 SQLAlchemy 对象读属性来构造，不用手动一个个字段抄
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ticker: str | None
    industry: str | None


class StatementCreate(BaseModel):
    # ge/le 是 Pydantic 的校验：财年必须在这个区间内，防止手滑输成 202 或 20233
    fiscal_year: int = Field(ge=1900, le=2100)

    revenue: float | None = None
    cost_of_goods_sold: float | None = None
    operating_income: float | None = None
    net_income: float | None = None

    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    inventory: float | None = None


class StatementOut(StatementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int


class RatioWarning(BaseModel):
    ratio: str
    value: float
    threshold: float
    message: str


class YearRatios(BaseModel):
    """某公司某一年的比率结果。"""

    fiscal_year: int
    ratios: dict[str, float | None]
    warnings: list[RatioWarning]


class CompanyRatios(BaseModel):
    """某公司所有年份的比率，按年份升序 —— 前端拿到直接就能画折线。"""

    company: CompanyOut
    years: list[YearRatios]


class ComparisonRow(BaseModel):
    """横向对比：同一年，一家公司的一行。"""

    company: CompanyOut
    fiscal_year: int
    ratios: dict[str, float | None]
    warnings: list[RatioWarning]
