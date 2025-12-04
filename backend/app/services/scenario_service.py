from __future__ import annotations

from typing import List, Tuple

from sqlalchemy.orm import Session

import routing_core
from app.models.db_models import Scenario, ScenarioModification
from app.models.dto import RouteRequest
from app.services.graph_manager import GraphManager


def _build_edges_for_scenario(
    manager: GraphManager,
    db: Session,
    scenario_id: int,
) -> List[Tuple[int, int, float]]:
    """
    Формує список ребер для сценарію:
      - бере базові ребра з GraphManager;
      - застосовує модифікації сценарію (disable / new_weight / weight_multiplier).
    """
    base_edges = manager.get_edges()
    mods = (
        db.query(ScenarioModification)
        .filter(ScenarioModification.scenario_id == scenario_id)
        .all()
    )

    mods_map = {
        (m.from_node, m.to_node): m
        for m in mods
    }

    result_edges: List[Tuple[int, int, float]] = []

    for from_node, to_node, base_weight in base_edges:
        mod = mods_map.get((from_node, to_node))

        if mod is None:
            # Нема модифікації — ребро залишається як є
            result_edges.append((from_node, to_node, base_weight))
            continue

        if mod.disable:
            # Ребро відключено в цьому сценарії
            continue

        weight = base_weight
        if mod.new_weight is not None:
            weight = mod.new_weight

        # Множник трафіку (1.0 означає "без змін")
        if mod.weight_multiplier is not None:
            weight = weight * mod.weight_multiplier

        result_edges.append((from_node, to_node, weight))

    return result_edges


def compute_route_in_scenario(
    manager: GraphManager,
    db: Session,
    req: RouteRequest,
) -> Tuple[float, List[int]]:
    """
    Обчислює маршрут в рамках обраного сценарію:
      - будує окремий PyGraph під сценарій;
      - запускає Dijkstra або A* на ньому.
    """
    if req.scenario_id is None:
        raise ValueError("scenario_id не заданий для сценарного запиту")

    scenario = (
        db.query(Scenario)
        .filter(
            Scenario.id == req.scenario_id,
            Scenario.is_active.is_(True),
        )
        .first()
    )

    if scenario is None:
        raise ValueError(f"Сценарій {req.scenario_id} не знайдено або він неактивний")

    edges = _build_edges_for_scenario(manager, db, scenario.id)

    # Будуємо окремий граф під сценарій
    g = routing_core.PyGraph()
    for from_node, to_node, weight in edges:
        g.add_edge(from_node, to_node, weight)

    if req.algorithm == "a_star":
        distance, path = g.shortest_path_a_star(req.source, req.target)
    else:
        distance, path = g.shortest_path_dijkstra(req.source, req.target)

    return float(distance), list(path)
