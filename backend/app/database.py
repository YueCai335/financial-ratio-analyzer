from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Single-file SQLite database; the file is created under backend/
SQLALCHEMY_DATABASE_URL = "sqlite:///./financials.db"

# check_same_thread=False is required for SQLite + FastAPI:
# FastAPI requests may run on different threads, and SQLite disallows
# reusing a connection across threads by default.
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
