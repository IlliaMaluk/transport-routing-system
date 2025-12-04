from __future__ import annotations

from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

import routing_core
from app.models.db_models import OptimizationProfile, EdgeMetadata
from app.services.graph_manager import GraphManager
from app.models.dto import RouteRequest


def get_profile_by_name(db: Session, name: str) -> OptimizationProfile | None:
    return (
        db.query(OptimizationProfile)
        .filter(OptimizationProfile.name == name)
        .first()
    )


def compute_route_with_profile(
    manager: GraphManager,
    db: Session,
    req: RouteRequest,
) -> Tuple[float, List[int]]:
    """
    Рахує маршрут із використанням профілю оптимізації.

    Вага ребра:
      W = w_time * travel_time + w_distance * distance + w_cost * cost

    Якщо метаданих немає, fallback на базову вагу з GraphManager.
    """
    if req.profile is None:
        raise ValueError("profile не заданий")

    profile = get_profile_by_name(db, req.profile)
    if profile is None:
        raise ValueError(f"Профіль '{req.profile}' не знайдено")

    edges = manager.get_edges()
    meta_rows = db.query(EdgeMetadata).all()
    meta_map: Dict[Tuple[int, int], EdgeMetadata] = {
        (m.from_node, m.to_node): m for m in meta_rows
    }

    w_time = profile.weight_time or 0.0
    w_dist = profile.weight_distance or 0.0
    w_cost = profile.weight_cost or 0.0

    g = routing_core.PyGraph()

    for from_node, to_node, base_weight in edges:
        meta = meta_map.get((from_node, to_node))

        if meta is not None:
            time_val = meta.travel_time if meta.travel_time is not None else base_weight
            dist_val = meta.distance if meta.distance is not None else 0.0
            cost_val = meta.cost if meta.cost is not None else 0.0
        else:
            time_val = base_weight
            dist_val = 0.0
            cost_val = 0.0

        agg = w_time * time_val + w_dist * dist_val + w_cost * cost_val

        # fallback, якщо вийшло 0 або негатив
        if not (agg > 0.0):
            agg = base_weight if base_weight > 0.0 else 1.0

        g.add_edge(from_node, to_node, agg)

    if req.algorithm == "a_star":
        distance, path = g.shortest_path_a_star(req.source, req.target)
    else:
        distance, path = g.shortest_path_dijkstra(req.source, req.target)

    return float(distance), list(path)
