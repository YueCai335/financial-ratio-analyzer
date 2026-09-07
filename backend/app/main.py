from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import health, models, ratios, schemas
from .database import Base, engine, get_db

# Create tables directly from models.py during development. A production
# project would use Alembic migrations, but this project's schema rarely
# changes once set, so that extra layer isn't introduced here.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Financial Ratio Analyzer",
    description="Enter key financial statement data, compute eight core "
    "financial ratios, and view trends and cross-company comparisons.",
)

# If the frontend were deployed separately (e.g. on Vercel), its domain
# would differ from the backend's and the browser would block cross-origin
# requests, hence CORS. This project serves the frontend from the same
# service, so it isn't strictly needed, but it's kept in case of a future
# split deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Names of every monetary field in models.py, used to pick out the data to
# feed into the calculation functions from a database object
FINANCIAL_FIELDS = [
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


def _to_fields(statement: models.FinancialStatement) -> dict:
    """Converts a database object into a plain dict to feed into
    ratios.calculate_all.

    This is the price of ratios.py not depending on SQLAlchemy, and also its
    payoff: the translation work is confined to this one function.
    """
    return {name: getattr(statement, name) for name in FINANCIAL_FIELDS}


def _year_result(statement: models.FinancialStatement) -> dict:
    computed = ratios.calculate_all(_to_fields(statement))
    return {
        "fiscal_year": statement.fiscal_year,
        "ratios": computed,
        "warnings": health.check(computed),
    }


def _get_company(db: Session, company_id: int) -> models.Company:
    company = db.get(models.Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@app.get("/api/health")
def healthcheck():
    return {"status": "ok"}


@app.get("/api/ratio-labels")
def ratio_labels():
    """Tells the frontend the display name and format (percent/times) for
    each ratio.

    Kept on the backend so there is only one copy to maintain — the
    frontend's wording never needs to be kept in sync separately.
    """
    return {
        key: {"label": label, "format": fmt}
        for key, (label, fmt) in ratios.RATIO_LABELS.items()
    }


# ---------- Companies ----------


@app.get("/api/companies", response_model=list[schemas.CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.scalars(select(models.Company).order_by(models.Company.name)).all()


@app.post("/api/companies", response_model=schemas.CompanyOut, status_code=201)
def create_company(payload: schemas.CompanyCreate, db: Session = Depends(get_db)):
    company = models.Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@app.delete("/api/companies/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = _get_company(db, company_id)
    # models.py configures the relationship with cascade="all, delete-orphan",
    # so deleting a company also deletes its statements — no orphan records left behind
    db.delete(company)
    db.commit()


# ---------- Financial statement data ----------


@app.get(
    "/api/companies/{company_id}/statements",
    response_model=list[schemas.StatementOut],
)
def list_statements(company_id: int, db: Session = Depends(get_db)):
    _get_company(db, company_id)
    return db.scalars(
        select(models.FinancialStatement)
        .where(models.FinancialStatement.company_id == company_id)
        .order_by(models.FinancialStatement.fiscal_year)
    ).all()


@app.post(
    "/api/companies/{company_id}/statements",
    response_model=schemas.StatementOut,
    status_code=201,
)
def create_statement(
    company_id: int,
    payload: schemas.StatementCreate,
    db: Session = Depends(get_db),
):
    _get_company(db, company_id)
    statement = models.FinancialStatement(company_id=company_id, **payload.model_dump())
    db.add(statement)
    try:
        db.commit()
    except IntegrityError:
        # Hit the UniqueConstraint in models.py: this company already has a
        # record for this year. Must roll back, or every later operation on
        # this session will fail.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Data for fiscal year {payload.fiscal_year} already "
            f"exists; delete it before re-entering",
        )
    db.refresh(statement)
    return statement


@app.delete("/api/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = db.get(models.FinancialStatement, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(statement)
    db.commit()


# ---------- Ratios ----------


@app.get("/api/companies/{company_id}/ratios", response_model=schemas.CompanyRatios)
def company_ratios(company_id: int, db: Session = Depends(get_db)):
    """All years of ratios for one company, ascending by year, ready for the
    frontend to plot as a line chart.
    """
    company = _get_company(db, company_id)
    statements = db.scalars(
        select(models.FinancialStatement)
        .where(models.FinancialStatement.company_id == company_id)
        .order_by(models.FinancialStatement.fiscal_year)
    ).all()
    return {
        "company": company,
        "years": [_year_result(s) for s in statements],
    }


@app.get("/api/compare", response_model=list[schemas.ComparisonRow])
def compare(fiscal_year: int, db: Session = Depends(get_db)):
    """Computes ratios for every company that has data in a given fiscal
    year, for a side-by-side bar chart.

    A real-world wrinkle worth noting: companies' fiscal years end on
    different dates (Apple in September, Microsoft in June, Walmart in
    January), so the "same fiscal_year" doesn't cover exactly the same
    economic period across companies — worth keeping in mind for strict
    comparisons.
    """
    rows = db.execute(
        select(models.Company, models.FinancialStatement)
        .join(models.FinancialStatement)
        .where(models.FinancialStatement.fiscal_year == fiscal_year)
        .order_by(models.Company.name)
    ).all()
    return [
        {"company": company, **_year_result(statement)} for company, statement in rows
    ]


@app.get("/api/years")
def available_years(db: Session = Depends(get_db)):
    """Which fiscal years have data in the database, for the frontend's year
    dropdown.
    """
    years = db.scalars(
        select(models.FinancialStatement.fiscal_year)
        .distinct()
        .order_by(models.FinancialStatement.fiscal_year.desc())
    ).all()
    return list(years)


# ---------- Frontend ----------

# Mounted last: FastAPI matches routes in registration order, so the
# /api/* routes registered above take priority, and everything else falls
# through to the static files. html=True makes "/" return index.html
# automatically.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
