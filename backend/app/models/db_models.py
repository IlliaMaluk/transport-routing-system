from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RouteQuery(Base):
    """
    Історія запитів пошуку маршруту.
    """

    __tablename__ = "route_queries"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    source_node = Column(Integer, nullable=False)
    target_node = Column(Integer, nullable=False)

    algorithm = Column(String(50), nullable=False)
    criteria = Column(String, nullable=False)  # JSON-рядок (list[str])
    profile = Column(String, nullable=True)

    total_weight = Column(Float, nullable=True)
    execution_time_ms = Column(Float, nullable=True)

    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(String, nullable=True)

    is_batch = Column(Boolean, nullable=False, default=False)
    batch_group = Column(String, nullable=True)

    scenario_id = Column(
        Integer,
        ForeignKey("scenarios.id"),
        nullable=True,
        index=True,
    )


class Scenario(Base):
    """
    Сценарій моделювання транспортної мережі.
    """

    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    name = Column(String(200), nullable=False, unique=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    modifications = relationship(
        "ScenarioModification",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class ScenarioModification(Base):
    """
    Модифікація мережі в рамках сценарію.
    """

    __tablename__ = "scenario_modifications"

    id = Column(Integer, primary_key=True, index=True)

    scenario_id = Column(
        Integer,
        ForeignKey("scenarios.id"),
        nullable=False,
        index=True,
    )

    from_node = Column(Integer, nullable=False)
    to_node = Column(Integer, nullable=False)

    disable = Column(Boolean, nullable=False, default=False)
    weight_multiplier = Column(Float, nullable=False, default=1.0)
    new_weight = Column(Float, nullable=True)

    scenario = relationship("Scenario", back_populates="modifications")


class GraphFixLog(Base):
    """
    Журнал виправлень графа (наприклад, видалення нульових циклів).
    """

    __tablename__ = "graph_fix_log"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    fix_type = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    details = Column(String, nullable=True)  # JSON з параметрами/результатами


class EdgeMetadata(Base):
    """
    Метадані про ребра:
      - тип (дорога/залізниця/громадський транспорт);
      - відстань, час, вартість, пропускна здатність;
      - односторонній рух.
    """

    __tablename__ = "edge_metadata"

    id = Column(Integer, primary_key=True, index=True)

    from_node = Column(Integer, nullable=False, index=True)
    to_node = Column(Integer, nullable=False, index=True)

    edge_type = Column(String(50), nullable=True)  # road / rail / transit / ...
    distance = Column(Float, nullable=True)        # км
    travel_time = Column(Float, nullable=True)     # хв/с
    cost = Column(Float, nullable=True)            # умовна валюта
    capacity = Column(Float, nullable=True)        # пропускна здатність
    is_one_way = Column(Boolean, nullable=False, default=True)


class OptimizationProfile(Base):
    """
    Профіль оптимізації: ваги для time/distance/cost + штраф за пересадки.
    """

    __tablename__ = "optimization_profiles"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    name = Column(String(100), nullable=False, unique=True)
    description = Column(String, nullable=True)

    weight_time = Column(Float, nullable=False, default=1.0)
    weight_distance = Column(Float, nullable=False, default=0.0)
    weight_cost = Column(Float, nullable=False, default=0.0)
    transfer_penalty = Column(Float, nullable=False, default=0.0)
