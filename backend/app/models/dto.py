from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# Допустимі критерії оптимізації
OptimizationCriterion = Literal["time", "distance", "cost", "transfers"]
# Допустимі алгоритми пошуку
AlgorithmType = Literal["dijkstra", "a_star"]


class EdgeCreate(BaseModel):
    from_node: int = Field(..., description="ID початкового вузла")
    to_node: int = Field(..., description="ID кінцевого вузла")
    weight: float = Field(..., description="Вага ребра (узагальнений cost)")


class EdgeBulkCreateRequest(BaseModel):
    """
    Запит для додавання відразу багатьох ребер.
    """
    edges: List[EdgeCreate]


class NodeCreate(BaseModel):
    id: int = Field(..., description="ID вузла")


class NodeBulkCreateRequest(BaseModel):
    """
    Запит для додавання явних вузлів (без ребер).
    """
    nodes: List[NodeCreate]


class GraphInfoResponse(BaseModel):
    """
    Відповідь зі статистикою про граф.
    """
    node_count: int
    edge_count: int


class RouteRequest(BaseModel):
    """
    Запит на пошук одного маршруту.
    """
    source: int
    target: int
    criteria: List[OptimizationCriterion] = Field(
        default_factory=lambda: ["time"],
        description="Список критеріїв оптимізації (time/distance/cost/transfers)",
    )
    profile: Optional[str] = Field(
        default=None,
        description="Назва профілю оптимізації (cargo, public_peak тощо)",
    )
    algorithm: AlgorithmType = Field(
        default="dijkstra",
        description="Алгоритм пошуку маршруту (dijkstra, a_star)",
    )
    scenario_id: Optional[int] = Field(
        default=None,
        description="ID сценарію моделювання, в рамках якого шукається маршрут",
    )


class RouteSegment(BaseModel):
    from_node: int
    to_node: int
    weight: float


class RouteResponse(BaseModel):
    total_weight: float
    nodes: List[int]
    segments: List[RouteSegment]
    algorithm: str
    execution_time_ms: float


class RouteBatchRequest(BaseModel):
    """
    Запит на паралельний пошук для багатьох маршрутів.
    """
    queries: List[RouteRequest]


class RouteBatchItem(BaseModel):
    """
    Один елемент відповіді для батч-запиту.
    """
    request: RouteRequest
    response: RouteResponse


class CsvImportResponse(BaseModel):
    """
    Результат імпорту графа з CSV.
    """
    edges_imported: int
    skipped_rows: int
    errors: List[str]
    node_count: int
    edge_count: int
    sample_rows: int


# ---------- Історія запитів та статистика ----------


class RouteHistoryItem(BaseModel):
    id: int
    created_at: datetime
    source: int
    target: int
    algorithm: str
    criteria: List[OptimizationCriterion]
    profile: Optional[str]
    total_weight: Optional[float]
    execution_time_ms: Optional[float]
    success: bool
    error_message: Optional[str]
    is_batch: bool
    batch_group: Optional[str]
    scenario_id: Optional[int]


class AlgorithmStats(BaseModel):
    algorithm: str
    query_count: int
    avg_execution_ms: Optional[float]
    max_execution_ms: Optional[float]


class PerformanceStatsResponse(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_execution_ms: Optional[float]
    max_execution_ms: Optional[float]
    per_algorithm: List[AlgorithmStats]


# ---------- Сценарії моделювання ----------


class ScenarioCreate(BaseModel):
    name: str = Field(..., description="Назва сценарію (унікальна)")
    description: Optional[str] = Field(None, description="Опис сценарію")


class ScenarioResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime


class ScenarioModificationCreate(BaseModel):
    from_node: int
    to_node: int
    disable: bool = Field(
        default=False,
        description="Якщо true — ребро буде відключене в цьому сценарії",
    )
    weight_multiplier: float = Field(
        default=1.0,
        description="Множник до базової ваги (1.0 — без змін)",
    )
    new_weight: Optional[float] = Field(
        default=None,
        description="Якщо задано — нова вага ребра (ігнорує базову вагу)",
    )


class ScenarioModificationItem(BaseModel):
    id: int
    from_node: int
    to_node: int
    disable: bool
    weight_multiplier: float
    new_weight: Optional[float]


class ScenarioDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    modifications: List[ScenarioModificationItem]


# ---------- Контроль якості графа ----------


class GraphQualityZeroCycle(BaseModel):
    nodes: List[int]


class GraphQualityCheckResponse(BaseModel):
    node_count: int
    edge_count: int
    isolated_nodes: List[int]
    zero_weight_cycles: List[GraphQualityZeroCycle]
    zero_cycle_limit_reached: bool


class GraphQualityFixResponse(BaseModel):
    removed_zero_weight_edges: int
    removed_isolated_nodes: int
    log_id: Optional[int]


# ---------- Метадані ребер ----------


class EdgeMetadataItem(BaseModel):
    from_node: int
    to_node: int
    edge_type: Optional[str]
    distance: Optional[float]
    travel_time: Optional[float]
    cost: Optional[float]
    capacity: Optional[float]
    is_one_way: bool


# ---------- Профілі оптимізації ----------


class OptimizationProfileCreate(BaseModel):
    name: str = Field(..., description="Назва профілю (унікальна)")
    description: Optional[str] = Field(None, description="Опис профілю")
    weight_time: float = Field(
        default=1.0,
        description="Вага для часу (travel_time)",
    )
    weight_distance: float = Field(
        default=0.0,
        description="Вага для відстані (distance)",
    )
    weight_cost: float = Field(
        default=0.0,
        description="Вага для вартості (cost)",
    )
    transfer_penalty: float = Field(
        default=0.0,
        description="Штраф за пересадку (поки не використовується явно)",
    )


class OptimizationProfileResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    weight_time: float
    weight_distance: float
    weight_cost: float
    transfer_penalty: float
    created_at: datetime


# ---------- Асинхронні batch-задачі ----------


class AsyncJobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "finished", "failed"]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_queries: int
    completed_queries: int
    error_message: Optional[str]
    execution_time_ms: Optional[float]
    result: Optional[List[RouteBatchItem]]


class AsyncJobsMetricsResponse(BaseModel):
    queue_length: int
    running_jobs: int
    finished_jobs: int
    failed_jobs: int
    avg_job_time_ms: Optional[float]
    cpu_usage_percent: Optional[float]
    gpu_usage_percent: Optional[float]

