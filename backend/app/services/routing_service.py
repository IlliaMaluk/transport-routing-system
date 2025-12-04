from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.dto import (
    RouteRequest,
    RouteResponse,
    RouteSegment,
    RouteBatchRequest,
    RouteBatchItem,
)
from app.models.db_models import RouteQuery
from app.services.graph_manager import GraphManager
from app.services.scenario_service import compute_route_in_scenario
from app.services.profile_service import compute_route_with_profile


def _log_query(
    db: Session,
    req: RouteRequest,
    distance: Optional[float],
    exec_ms: Optional[float],
    success: bool,
    error_message: Optional[str],
    is_batch: bool,
    batch_group: Optional[str],
    algorithm_label: str,
) -> None:
    """
    Зберігає запис у таблицю route_queries.
    """
    db_obj = RouteQuery(
        source_node=req.source,
        target_node=req.target,
        algorithm=algorithm_label,
        criteria=json.dumps(list(req.criteria)),
        profile=req.profile,
        total_weight=distance if success else None,
        execution_time_ms=exec_ms if success else None,
        success=success,
        error_message=error_message,
        is_batch=is_batch,
        batch_group=batch_group,
        scenario_id=req.scenario_id,
    )
    db.add(db_obj)
    db.commit()


def find_route(
    manager: GraphManager,
    req: RouteRequest,
    db: Optional[Session] = None,
) -> RouteResponse:
    """
    Пошук маршруту з урахуванням:
      - алгоритму (dijkstra / a_star),
      - (опціонально) сценарію,
      - (опціонально) профілю оптимізації.
    """
    algo = req.algorithm
    algo_label = algo
    start = time.perf_counter()
    error_msg: Optional[str] = None
    success = True

    try:
        if req.scenario_id is not None:
            # Поки що комбінація сценарій + профіль не підтримується
            if req.profile is not None:
                raise ValueError(
                    "Комбінація scenario_id та profile поки не підтримується"
                )
            if db is None:
                raise ValueError("DB session is required для сценаріїв")
            distance, path = compute_route_in_scenario(manager, db, req)
            algo_label = f"{algo}_scenario"
        elif req.profile is not None:
            if db is None:
                raise ValueError("DB session is required для профілів оптимізації")
            distance, path = compute_route_with_profile(manager, db, req)
            algo_label = f"{algo}_profile"
        else:
            # Базовий граф без профілю/сценарію
            if algo == "a_star":
                distance, path = manager.shortest_path_a_star(req.source, req.target)
            else:
                distance, path = manager.shortest_path_dijkstra(req.source, req.target)
            algo_label = algo
    except Exception as exc:  # noqa: BLE001
        distance = float("inf")
        path = []
        success = False
        error_msg = str(exc)

    end = time.perf_counter()
    exec_ms = (end - start) * 1000.0

    segments: List[RouteSegment] = []
    for i in range(len(path) - 1):
        segments.append(
            RouteSegment(from_node=path[i], to_node=path[i + 1], weight=0.0)
        )

    if db is not None:
        _log_query(
            db=db,
            req=req,
            distance=distance,
            exec_ms=exec_ms,
            success=success,
            error_message=error_msg,
            is_batch=False,
            batch_group=None,
            algorithm_label=algo_label,
        )

    return RouteResponse(
        total_weight=distance,
        nodes=path,
        segments=segments,
        algorithm=algo_label,
        execution_time_ms=exec_ms,
    )


def find_routes_batch(
    manager: GraphManager,
    batch: RouteBatchRequest,
    db: Optional[Session] = None,
) -> List[RouteBatchItem]:
    """
    Паралельний пошук для множини маршрутів.
    Обмеження: batch-пошук працює тільки для базового графа (без сценаріїв і профілів).
    """
    if any(r.scenario_id is not None for r in batch.queries):
        raise ValueError("scenario_id у batch-запитах наразі не підтримується")
    if any(r.profile is not None for r in batch.queries):
        raise ValueError("profile у batch-запитах наразі не підтримується")

    queries_pairs = [(r.source, r.target) for r in batch.queries]

    start = time.perf_counter()
    results = manager.shortest_paths_batch(queries_pairs)
    end = time.perf_counter()
    total_time_ms = (end - start) * 1000.0

    batch_group_id: Optional[str] = None
    if db is not None:
        batch_group_id = str(uuid.uuid4())

    items: List[RouteBatchItem] = []
    for req, (distance, path) in zip(batch.queries, results):
        segments: List[RouteSegment] = []
        for i in range(len(path) - 1):
            segments.append(
                RouteSegment(from_node=path[i], to_node=path[i + 1], weight=0.0)
            )

        route_resp = RouteResponse(
            total_weight=distance,
            nodes=path,
            segments=segments,
            algorithm="dijkstra_parallel_batch",
            execution_time_ms=total_time_ms,
        )

        if db is not None:
            _log_query(
                db=db,
                req=req,
                distance=distance,
                exec_ms=total_time_ms,
                success=True,
                error_message=None,
                is_batch=True,
                batch_group=batch_group_id,
                algorithm_label="dijkstra_parallel_batch",
            )

        items.append(RouteBatchItem(request=req, response=route_resp))

    return items
