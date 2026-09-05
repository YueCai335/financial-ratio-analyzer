from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite 单文件数据库，文件会生成在 backend/ 目录下
SQLALCHEMY_DATABASE_URL = "sqlite:///./financials.db"

# check_same_thread=False 是 SQLite + FastAPI 的固定要求：
# FastAPI 的请求可能跑在不同线程里，SQLite 默认禁止跨线程复用连接
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
