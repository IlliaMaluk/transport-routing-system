from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.dto import RouteBatchRequest, RouteBatchItem
from app.services.graph_manager import get_or_create_graph_manager
from app.services.routing_service import find_routes_batch


@dataclass
class RoutingJob:
    """
    Опис однієї асинхронної batch-задачі.
    """
    id: str
    request: RouteBatchRequest
    status: str = "queued"  # queued | running | finished | failed
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[List[RouteBatchItem]] = None

    @property
    def total_queries(self) -> int:
        return len(self.request.queries)

    @property
    def completed_queries(self) -> int:
        return len(self.result) if self.result is not None else 0

    @property
    def execution_time_ms(self) -> Optional[float]:
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at) * 1000.0


class RoutingJobManager:
    """
    Менеджер асинхронних batch-задач:
      - власний ThreadPoolExecutor;
      - внутрішня черга задач (jobs зі статусом queued);
      - прості метрики (кількість задач, середній час, CPU).
    """

    def __init__(self, max_workers: Optional[int] = None) -> None:
        if max_workers is None:
            cpu = os.cpu_count() or 4
            max_workers = max(2, min(32, cpu * 2))
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, RoutingJob] = {}
        self._lock = threading.Lock()
        self._completed_times: List[float] = []

    def submit(self, request: RouteBatchRequest) -> RoutingJob:
        """
        Створює задачу, ставить у чергу та відправляє у ThreadPool.
        """
        job_id = str(uuid.uuid4())
        job = RoutingJob(id=job_id, request=request)
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run_job, job_id)
        return job

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.started_at = time.time()

        db: Session = SessionLocal()
        try:
            # Використовуємо існуючий паралельний batch-пошук
            manager = get_or_create_graph_manager()
            result = find_routes_batch(manager, job.request, db)
            finished_at = time.time()
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job.result = result
                job.status = "finished"
                job.finished_at = finished_at
                if job.execution_time_ms is not None:
                    self._completed_times.append(job.execution_time_ms)
        except Exception as exc:  # noqa: BLE001
            finished_at = time.time()
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                job.status = "failed"
                job.error_message = str(exc)
                job.finished_at = finished_at
        finally:
            db.close()

    def get_job(self, job_id: str) -> Optional[RoutingJob]:
        """
        Повертає копію стану задачі, щоб не ловити гонки.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return RoutingJob(
                id=job.id,
                request=job.request,
                status=job.status,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
                error_message=job.error_message,
                result=job.result,
            )

    def get_metrics(self) -> Dict[str, Optional[float | int]]:
        """
        Повертає агреговані метрики по асинхронних задачах.
        """
        with self._lock:
            queue_len = sum(1 for j in self._jobs.values() if j.status == "queued")
            running = sum(1 for j in self._jobs.values() if j.status == "running")
            finished = sum(1 for j in self._jobs.values() if j.status == "finished")
            failed = sum(1 for j in self._jobs.values() if j.status == "failed")
            avg_time = (
                sum(self._completed_times) / len(self._completed_times)
                if self._completed_times
                else None
            )

        try:
            cpu = psutil.cpu_percent(interval=0.0)
        except Exception:
            cpu = None

        return {
            "queue_length": queue_len,
            "running_jobs": running,
            "finished_jobs": finished,
            "failed_jobs": failed,
            "avg_job_time_ms": avg_time,
            "cpu_usage_percent": cpu,
            "gpu_usage_percent": None,  # GPU наразі не використовується
        }


routing_job_manager = RoutingJobManager()
