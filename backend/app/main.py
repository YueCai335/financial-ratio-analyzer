from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import health, models, ratios, schemas
from .database import Base, engine, get_db

# 开发阶段直接按 models.py 建表。生产项目会用 Alembic 做迁移，
# 但这个项目表结构一旦定下来就不怎么改，先不引入那层复杂度。
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Financial Ratio Analyzer",
    description="输入财报关键数据，计算八个核心财务比率，展示趋势与横向对比",
)

# 前端如果单独部署在 Vercel，域名和后端不同，浏览器会拦跨域请求，所以要开 CORS。
# 本项目前端由同一个服务托管，其实用不到，但留着方便以后拆开部署。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# models.py 里所有金额字段的名字，用来从数据库对象里挑出要送进计算函数的数据
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
    """把数据库对象转成普通 dict，好喂给 ratios.calculate_all。

    这一步就是 ratios.py 不依赖 SQLAlchemy 的代价，也是它的价值所在：
    翻译工作集中在这一个函数里。
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
        raise HTTPException(status_code=404, detail="公司不存在")
    return company


@app.get("/api/health")
def healthcheck():
    return {"status": "ok"}


@app.get("/api/ratio-labels")
def ratio_labels():
    """告诉前端每个比率叫什么中文名、该按百分比还是倍数显示。

    放在后端是为了只维护一份，前端改文案不用两边同步。
    """
    return {
        key: {"label": label, "format": fmt}
        for key, (label, fmt) in ratios.RATIO_LABELS.items()
    }


# ---------- 公司 ----------


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
    # models.py 里 relationship 配了 cascade="all, delete-orphan"，
    # 删公司时它名下的财报会一起删掉，不会留下无主的孤儿记录
    db.delete(company)
    db.commit()


# ---------- 财报数据 ----------


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
        # 撞上了 models.py 里的 UniqueConstraint：这家公司这一年已经录过了。
        # 必须 rollback，否则这个 session 后面所有操作都会失败。
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{payload.fiscal_year} 年的数据已存在，请先删除再重录",
        )
    db.refresh(statement)
    return statement


@app.delete("/api/statements/{statement_id}", status_code=204)
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    statement = db.get(models.FinancialStatement, statement_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(statement)
    db.commit()


# ---------- 比率 ----------


@app.get("/api/companies/{company_id}/ratios", response_model=schemas.CompanyRatios)
def company_ratios(company_id: int, db: Session = Depends(get_db)):
    """一家公司所有年份的比率，按年份升序，前端拿到直接画折线图。"""
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
    """同一个财年，所有有数据的公司各算一遍，用来画并排柱状图。

    注意一个真实世界的坑：各家财年结束日期不同（苹果 9 月、微软 6 月、沃尔玛 1 月），
    所谓"同一个 fiscal_year"其实覆盖的经济周期不完全一样，严格比较时要留意。
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
    """数据库里有哪些年份有数据，给前端的年份下拉框用。"""
    years = db.scalars(
        select(models.FinancialStatement.fiscal_year)
        .distinct()
        .order_by(models.FinancialStatement.fiscal_year.desc())
    ).all()
    return list(years)


# ---------- 前端 ----------

# 挂在最后：FastAPI 按注册顺序匹配路由，先注册的 /api/* 优先，
# 剩下的路径才交给静态文件。html=True 让 "/" 自动返回 index.html。
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
