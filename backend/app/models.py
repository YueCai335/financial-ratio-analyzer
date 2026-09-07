from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Company(Base):
    # The table name in the database
    __tablename__ = "companies"

    # Mapped[int] = stores an integer
    # primary_key=True = row number, auto-increments 1,2,3..., never set manually
    id: Mapped[int] = mapped_column(primary_key=True)

    # Mapped[str] = stores text, no "| None" means required (NOT NULL at the DB level)
    # String(100) = max length 100 characters
    name: Mapped[str] = mapped_column(String(100))

    # Mapped[str | None] = stores text, may be empty. "| None" means "allowed to be missing"
    ticker: Mapped[str | None] = mapped_column(String(10))
    industry: Mapped[str | None] = mapped_column(String(50))

    # Not a real database column — a Python-side convenience:
    # once you have a company object, company.statements is a list of all its
    # yearly financial statements
    statements: Mapped[list["FinancialStatement"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )


class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key: which company this statement belongs to.
    # Stores an id from the companies table.
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))

    fiscal_year: Mapped[int] = mapped_column()

    # ---- Income statement ----
    # Float = stores decimals. Floats have rounding error (0.1 + 0.2 != 0.3),
    # which is unacceptable in a real accounting ledger. Here they only feed
    # ratio math and charts, where the error is many decimal places out and
    # never changes a conclusion. Trade-off discussed in the README.
    revenue: Mapped[float | None] = mapped_column(Float)
    cost_of_goods_sold: Mapped[float | None] = mapped_column(Float)
    operating_income: Mapped[float | None] = mapped_column(Float)
    net_income: Mapped[float | None] = mapped_column(Float)

    # ---- Balance sheet ----
    total_assets: Mapped[float | None] = mapped_column(Float)
    total_liabilities: Mapped[float | None] = mapped_column(Float)
    total_equity: Mapped[float | None] = mapped_column(Float)
    current_assets: Mapped[float | None] = mapped_column(Float)
    current_liabilities: Mapped[float | None] = mapped_column(Float)
    inventory: Mapped[float | None] = mapped_column(Float)

    # All amount fields are nullable: when transcribing numbers from a filing,
    # a particular line item may be temporarily unavailable — store what you
    # have and the other ratios still compute. A ratio that can't be computed
    # shows "—" instead of blocking the whole row from being saved.

    # Reverse convenience: statement.company gives the owning company object
    company: Mapped["Company"] = relationship(back_populates="statements")

    # A given company can only have one record per fiscal year — enforced at
    # the database level, so a bug that inserts a duplicate gets rejected
    # automatically instead of silently corrupting the data.
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_company_year"),
    )
