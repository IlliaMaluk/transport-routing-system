from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.database import SessionLocal
from fastapi import HTTPException, status

from app.services.graph_manager import GraphManager, get_or_create_graph_manager


def get_graph_manager() -> GraphManager:
    """
    Dependency для FastAPI — глобальний GraphManager.
    """
    try:
        return get_or_create_graph_manager()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


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
