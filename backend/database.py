                            """
数据库模块
"""
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from backend.config import get_settings

settings = get_settings()

db_path = settings.db_path
db_dir = Path(db_path).parent
db_dir.mkdir(parents=True, exist_ok=True)

if settings.db_type == "sqlite":
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        f"postgresql://{settings.db_username}:{settings.db_password}@"
        f"{settings.db_host}:{settings.db_port}/{settings.db_database}"
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.models import stock, backtest as bt  # noqa
    Base.metadata.create_all(bind=engine)
