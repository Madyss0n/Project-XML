from pathlib import Path
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
from app.models import Base
from app.logger import setup_logger

logger = setup_logger(__name__)

DATABASE_PATH = Path(__file__).resolve().parent.parent / "books.db"
DATABASE_URL = URL.create("sqlite", database=str(DATABASE_PATH))

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Создаёт таблицы, если их ещё нет."""
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы БД готовы: %s", DATABASE_PATH)
