"""Pydantic models: define what the API's input and output look like.

The distinction from models.py trips people up:
  models.py  = how data is stored in the database (SQLAlchemy)
  schemas.py = how data is transmitted over the network (Pydantic)
Keeping them separate means extra fields stored in the database are never
accidentally exposed to the frontend, and garbage data sent by the frontend
is rejected by Pydantic before it ever reaches the database.
"""

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    ticker: str | None = Field(default=None, max_length=10)
    industry: str | None = Field(default=None, max_length=50)


class CompanyOut(BaseModel):
    # Allows building this directly from a SQLAlchemy object's attributes,
    # instead of copying each field by hand
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ticker: str | None
    industry: str | None


class StatementCreate(BaseModel):
    # ge/le are Pydantic validators: the fiscal year must fall in this range,
    # guarding against a typo like 202 or 20233
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
    """Ratio results for one company in one year."""

    fiscal_year: int
    ratios: dict[str, float | None]
    warnings: list[RatioWarning]


class CompanyRatios(BaseModel):
    """All years of ratios for one company, ascending by year — the frontend
    can plot this straight into a line chart.
    """

    company: CompanyOut
    years: list[YearRatios]


class ComparisonRow(BaseModel):
    """Side-by-side comparison: one company's row for a given year."""

    company: CompanyOut
    fiscal_year: int
    ratios: dict[str, float | None]
    warnings: list[RatioWarning]
