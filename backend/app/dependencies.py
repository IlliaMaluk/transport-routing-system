from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.graph_manager import GraphManager, graph_manager


def get_graph_manager() -> GraphManager:
    """
    Dependency для FastAPI — глобальний GraphManager.
    """
    return graph_manager


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для FastAPI — сесія БД (SQLAlchemy Session).

    Використання:
      db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
