from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_graph_manager, get_db
from app.models.dto import (
    EdgeBulkCreateRequest,
    GraphInfoResponse,
    RouteRequest,
    RouteResponse,
    RouteBatchRequest,
    RouteBatchItem,
    CsvImportResponse,
    RouteHistoryItem,
    PerformanceStatsResponse,
    AlgorithmStats,
    ScenarioCreate,
    ScenarioResponse,
    ScenarioDetailResponse,
    ScenarioModificationCreate,
    ScenarioModificationItem,
    NodeBulkCreateRequest,
    GraphQualityCheckResponse,
    GraphQualityZeroCycle,
    GraphQualityFixResponse,
    EdgeMetadataItem,
    OptimizationProfileCreate,
    OptimizationProfileResponse,
    AsyncJobStatus,
    AsyncJobsMetricsResponse,
)
from app.models.db_models import (
    RouteQuery,
    Scenario,
    ScenarioModification,
    EdgeMetadata,
    OptimizationProfile,
)
from app.services.graph_manager import GraphManager
from app.services.routing_service import find_route, find_routes_batch
from app.services.csv_import_service import import_edges_from_csv
from app.services.graph_quality_service import analyze_graph_quality, fix_graph_quality
from app.services.job_manager import routing_job_manager, RoutingJob

router = APIRouter()


# ---------- Допоміжне: конвертація RoutingJob -> AsyncJobStatus ----------


def _job_to_dto(job: RoutingJob) -> AsyncJobStatus:
    created_at_dt = datetime.fromtimestamp(job.created_at)
    started_at_dt = datetime.fromtimestamp(job.started_at) if job.started_at is not None else None
    finished_at_dt = datetime.fromtimestamp(job.finished_at) if job.finished_at is not None else None

    return AsyncJobStatus(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        created_at=created_at_dt,
        started_at=started_at_dt,
        finished_at=finished_at_dt,
        total_queries=job.total_queries,
        completed_queries=job.completed_queries,
        error_message=job.error_message,
        execution_time_ms=job.execution_time_ms,
        result=job.result,
    )


# ---------- Граф: інформація, вузли, ребра, імпорт ----------


@router.get("/graph/info", response_model=GraphInfoResponse)
def get_graph_info(
    manager: GraphManager = Depends(get_graph_manager),
) -> GraphInfoResponse:
    node_count, edge_count = manager.stats()
    return GraphInfoResponse(node_count=node_count, edge_count=edge_count)


@router.post("/graph/nodes", response_model=GraphInfoResponse)
def add_nodes(
    payload: NodeBulkCreateRequest,
    manager: GraphManager = Depends(get_graph_manager),
) -> GraphInfoResponse:
    for node in payload.nodes:
        manager.add_node(node.id)
    node_count, edge_count = manager.stats()
    return GraphInfoResponse(node_count=node_count, edge_count=edge_count)


@router.post("/graph/edges", response_model=GraphInfoResponse)
def add_edges(
    payload: EdgeBulkCreateRequest,
    manager: GraphManager = Depends(get_graph_manager),
) -> GraphInfoResponse:
    edges_tuples = [
        (edge.from_node, edge.to_node, edge.weight)
        for edge in payload.edges
    ]
    manager.add_edges(edges_tuples)
    node_count, edge_count = manager.stats()
    return GraphInfoResponse(node_count=node_count, edge_count=edge_count)


@router.post("/graph/import/csv", response_model=CsvImportResponse)
def import_graph_from_csv(
    file: UploadFile = File(..., description="CSV з from/to/weight та опціональними метаданими"),
    manager: GraphManager = Depends(get_graph_manager),
    db: Session = Depends(get_db),
) -> CsvImportResponse:
    summary = import_edges_from_csv(manager, file, db)
    node_count, edge_count = manager.stats()

    return CsvImportResponse(
        edges_imported=summary.edges_imported,
        skipped_rows=summary.skipped_rows,
        errors=summary.errors,
        node_count=node_count,
        edge_count=edge_count,
        sample_rows=summary.sample_rows,
    )


@router.get("/graph/edges/metadata", response_model=List[EdgeMetadataItem])
def list_edge_metadata(
    edge_type: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[EdgeMetadataItem]:
    """
    Метадані ребер (тип: road/rail/transit, дистанція, час, вартість, capacity, one-way).
    """
    query = db.query(EdgeMetadata)
    if edge_type:
        query = query.filter(EdgeMetadata.edge_type == edge_type)

    rows = query.limit(5000).all()

    return [
        EdgeMetadataItem(
            from_node=row.from_node,
            to_node=row.to_node,
            edge_type=row.edge_type,
            distance=row.distance,
            travel_time=row.travel_time,
            cost=row.cost,
            capacity=row.capacity,
            is_one_way=row.is_one_way,
        )
        for row in rows
    ]


# ---------- Контроль якості графа ----------


@router.get("/graph/quality/check", response_model=GraphQualityCheckResponse)
def check_graph_quality(
    manager: GraphManager = Depends(get_graph_manager),
) -> GraphQualityCheckResponse:
    quality = analyze_graph_quality(manager)
    node_count, edge_count = manager.stats()

    zero_cycles = [
        GraphQualityZeroCycle(nodes=cycle)
        for cycle in quality.zero_weight_cycles
    ]

    return GraphQualityCheckResponse(
        node_count=node_count,
        edge_count=edge_count,
        isolated_nodes=quality.isolated_nodes,
        zero_weight_cycles=zero_cycles,
        zero_cycle_limit_reached=quality.zero_cycle_limit_reached,
    )


@router.post("/graph/quality/fix", response_model=GraphQualityFixResponse)
def fix_graph_quality_endpoint(
    manager: GraphManager = Depends(get_graph_manager),
    db: Session = Depends(get_db),
) -> GraphQualityFixResponse:
    quality = analyze_graph_quality(manager)
    fix_result = fix_graph_quality(manager, db, quality)

    return GraphQualityFixResponse(
        removed_zero_weight_edges=fix_result.removed_zero_weight_edges,
        removed_isolated_nodes=fix_result.removed_isolated_nodes,
        log_id=fix_result.log_id,
    )


# ---------- Пошук маршрутів (синхронний) ----------


@router.post("/routes", response_model=RouteResponse)
def compute_route(
    request: RouteRequest,
    manager: GraphManager = Depends(get_graph_manager),
    db: Session = Depends(get_db),
) -> RouteResponse:
    return find_route(manager, request, db)


@router.post("/routes/batch", response_model=List[RouteBatchItem])
def compute_routes_batch(
    batch_request: RouteBatchRequest,
    manager: GraphManager = Depends(get_graph_manager),
    db: Session = Depends(get_db),
) -> List[RouteBatchItem]:
    return find_routes_batch(manager, batch_request, db)


# ---------- Пошук маршрутів (асинхронний batch + моніторинг) ----------


@router.post("/routes/async/submit", response_model=AsyncJobStatus)
def submit_async_routes(
    batch_request: RouteBatchRequest,
) -> AsyncJobStatus:
    """
    Створює асинхронну batch-задачу пошуку маршрутів.
    """
    job = routing_job_manager.submit(batch_request)
    return _job_to_dto(job)


@router.get("/routes/async/{job_id}", response_model=AsyncJobStatus)
def get_async_job(job_id: str) -> AsyncJobStatus:
    """
    Повертає стан асинхронної задачі (та результат, якщо завершена).
    """
    job = routing_job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_dto(job)


@router.get("/routes/async/metrics", response_model=AsyncJobsMetricsResponse)
def get_async_metrics() -> AsyncJobsMetricsResponse:
    """
    Метрики по асинхронних задачах.
    """
    metrics = routing_job_manager.get_metrics()
    return AsyncJobsMetricsResponse(**metrics)


# ---------- Історія запитів ----------


@router.get("/history/queries", response_model=List[RouteHistoryItem])
def get_query_history(
    limit: int = 50,
    algorithm: Optional[str] = None,
    only_failed: bool = False,
    db: Session = Depends(get_db),
) -> List[RouteHistoryItem]:
    query = db.query(RouteQuery).order_by(RouteQuery.created_at.desc())

    if algorithm:
        query = query.filter(RouteQuery.algorithm == algorithm)

    if only_failed:
        query = query.filter(RouteQuery.success.is_(False))

    rows = query.limit(limit).all()

    items: List[RouteHistoryItem] = []
    for row in rows:
        try:
            criteria_list = json.loads(row.criteria)
        except Exception:  # noqa: BLE001
            criteria_list = []

        items.append(
            RouteHistoryItem(
                id=row.id,
                created_at=row.created_at,
                source=row.source_node,
                target=row.target_node,
                algorithm=row.algorithm,
                criteria=criteria_list,
                profile=row.profile,
                total_weight=row.total_weight,
                execution_time_ms=row.execution_time_ms,
                success=row.success,
                error_message=row.error_message,
                is_batch=row.is_batch,
                batch_group=row.batch_group,
                scenario_id=row.scenario_id,
            )
        )

    return items


# ---------- Статистика продуктивності ----------


@router.get("/stats/performance", response_model=PerformanceStatsResponse)
def get_performance_stats(
    db: Session = Depends(get_db),
) -> PerformanceStatsResponse:
    total = db.query(func.count(RouteQuery.id)).scalar() or 0
    successful = (
        db.query(func.count(RouteQuery.id))
        .filter(RouteQuery.success.is_(True))
        .scalar()
        or 0
    )
    failed = total - successful

    avg_exec = (
        db.query(func.avg(RouteQuery.execution_time_ms))
        .filter(RouteQuery.success.is_(True))
        .scalar()
    )
    max_exec = (
        db.query(func.max(RouteQuery.execution_time_ms))
        .filter(RouteQuery.success.is_(True))
        .scalar()
    )

    per_algo_raw = (
        db.query(
            RouteQuery.algorithm,
            func.count(RouteQuery.id),
            func.avg(RouteQuery.execution_time_ms),
            func.max(RouteQuery.execution_time_ms),
        )
        .filter(RouteQuery.success.is_(True))
        .group_by(RouteQuery.algorithm)
        .all()
    )

    per_algorithm: List[AlgorithmStats] = [
        AlgorithmStats(
            algorithm=algo,
            query_count=count,
            avg_execution_ms=avg_ms,
            max_execution_ms=max_ms,
        )
        for algo, count, avg_ms, max_ms in per_algo_raw
    ]

    return PerformanceStatsResponse(
        total_queries=total,
        successful_queries=successful,
        failed_queries=failed,
        avg_execution_ms=avg_exec,
        max_execution_ms=max_exec,
        per_algorithm=per_algorithm,
    )


# ---------- Сценарії моделювання ----------


@router.post("/scenarios", response_model=ScenarioResponse)
def create_scenario(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
) -> ScenarioResponse:
    existing = (
        db.query(Scenario)
        .filter(Scenario.name == payload.name)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Сценарій з такою назвою вже існує")

    scenario = Scenario(
        name=payload.name,
        description=payload.description,
        is_active=True,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        is_active=scenario.is_active,
        created_at=scenario.created_at,
    )


@router.get("/scenarios", response_model=List[ScenarioResponse])
def list_scenarios(
    db: Session = Depends(get_db),
) -> List[ScenarioResponse]:
    rows = db.query(Scenario).order_by(Scenario.created_at.desc()).all()
    return [
        ScenarioResponse(
            id=row.id,
            name=row.name,
            description=row.description,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
) -> ScenarioDetailResponse:
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Сценарій не знайдено")

    mods = (
        db.query(ScenarioModification)
        .filter(ScenarioModification.scenario_id == scenario.id)
        .all()
    )

    mod_items: List[ScenarioModificationItem] = [
        ScenarioModificationItem(
            id=m.id,
            from_node=m.from_node,
            to_node=m.to_node,
            disable=m.disable,
            weight_multiplier=m.weight_multiplier,
            new_weight=m.new_weight,
        )
        for m in mods
    ]

    return ScenarioDetailResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        is_active=scenario.is_active,
        created_at=scenario.created_at,
        modifications=mod_items,
    )


@router.post("/scenarios/{scenario_id}/modifications", response_model=ScenarioDetailResponse)
def add_scenario_modifications(
    scenario_id: int,
    payload: List[ScenarioModificationCreate],
    db: Session = Depends(get_db),
) -> ScenarioDetailResponse:
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if scenario is None:
        raise HTTPException(status_code=404, detail="Сценарій не знайдено")

    for item in payload:
        mod = ScenarioModification(
            scenario_id=scenario.id,
            from_node=item.from_node,
            to_node=item.to_node,
            disable=item.disable,
            weight_multiplier=item.weight_multiplier,
            new_weight=item.new_weight,
        )
        db.add(mod)

    db.commit()

    return get_scenario(scenario_id=scenario.id, db=db)


# ---------- Профілі оптимізації ----------


@router.post("/profiles", response_model=OptimizationProfileResponse)
def create_profile(
    payload: OptimizationProfileCreate,
    db: Session = Depends(get_db),
) -> OptimizationProfileResponse:
    existing = (
        db.query(OptimizationProfile)
        .filter(OptimizationProfile.name == payload.name)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail="Профіль з такою назвою вже існує")

    profile = OptimizationProfile(
        name=payload.name,
        description=payload.description,
        weight_time=payload.weight_time,
        weight_distance=payload.weight_distance,
        weight_cost=payload.weight_cost,
        transfer_penalty=payload.transfer_penalty,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return OptimizationProfileResponse(
        id=profile.id,
        name=profile.name,
        description=profile.description,
        weight_time=profile.weight_time,
        weight_distance=profile.weight_distance,
        weight_cost=profile.weight_cost,
        transfer_penalty=profile.transfer_penalty,
        created_at=profile.created_at,
    )


@router.get("/profiles", response_model=List[OptimizationProfileResponse])
def list_profiles(
    db: Session = Depends(get_db),
) -> List[OptimizationProfileResponse]:
    rows = (
        db.query(OptimizationProfile)
        .order_by(OptimizationProfile.created_at.desc())
        .all()
    )
    return [
        OptimizationProfileResponse(
            id=row.id,
            name=row.name,
            description=row.description,
            weight_time=row.weight_time,
            weight_distance=row.weight_distance,
            weight_cost=row.weight_cost,
            transfer_penalty=row.transfer_penalty,
            created_at=row.created_at,
        )
        for row in rows
    ]
