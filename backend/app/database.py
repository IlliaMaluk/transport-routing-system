from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Простий варіант для дипломного проєкту — SQLite-файл у корені backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./routing.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # потрібно для SQLite + багатопоточності
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
