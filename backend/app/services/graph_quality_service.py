from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from sqlalchemy.orm import Session

from app.models.db_models import GraphFixLog
from app.services.graph_manager import GraphManager


@dataclass
class GraphQualityResult:
    isolated_nodes: List[int]
    zero_weight_cycles: List[List[int]]
    zero_cycle_limit_reached: bool


@dataclass
class GraphQualityFixResult:
    removed_zero_weight_edges: int
    removed_isolated_nodes: int
    log_id: int | None


def analyze_graph_quality(
    manager: GraphManager,
    max_cycles: int = 50,
    max_depth: int = 10,
    eps: float = 1e-9,
) -> GraphQualityResult:
    """
    Аналізує граф:
      - знаходить ізольовані вузли (без ребер);
      - знаходить цикли, де всі ребра мають вагу ≈ 0 (нульові цикли).
    """

    edges = manager.get_edges()
    nodes = manager.get_nodes()

    # Ізольовані вузли: ті, що не зустрічаються в жодному ребрі
    nodes_with_edges: Set[int] = set()
    for u, v, _ in edges:
        nodes_with_edges.add(u)
        nodes_with_edges.add(v)

    isolated_nodes = sorted(n for n in nodes if n not in nodes_with_edges)

    # Нульові цикли: будуємо граф тільки з ребер вагою ~0
    adj: Dict[int, List[int]] = {}
    for u, v, w in edges:
        if abs(w) <= eps:
            adj.setdefault(u, []).append(v)

    zero_cycles: List[List[int]] = []
    seen_cycles: Set[Tuple[int, ...]] = set()
    limit_reached = False

    def dfs(start: int, current: int, path: List[int], depth: int) -> None:
        nonlocal limit_reached
        if limit_reached:
            return
        if depth >= max_depth:
            return

        for nxt in adj.get(current, []):
            # замкнулися в цикл
            if nxt == start and depth >= 0:
                core = path[:]  # path: [start, ..., current]
                if len(core) >= 1:
                    # канонічне представлення (щоб не дублювати цикл з різних стартів)
                    min_val = min(core)
                    min_idx = core.index(min_val)
                    norm = tuple(core[min_idx:] + core[:min_idx])
                    if norm not in seen_cycles:
                        seen_cycles.add(norm)
                        zero_cycles.append(core)
                        if len(zero_cycles) >= max_cycles:
                            limit_reached = True
                            return
            elif nxt not in path:
                path.append(nxt)
                dfs(start, nxt, path, depth + 1)
                path.pop()

    for start in adj.keys():
        if limit_reached:
            break
        dfs(start, start, [start], 0)

    return GraphQualityResult(
        isolated_nodes=isolated_nodes,
        zero_weight_cycles=zero_cycles,
        zero_cycle_limit_reached=limit_reached,
    )


def fix_graph_quality(
    manager: GraphManager,
    db: Session,
    quality: GraphQualityResult,
) -> GraphQualityFixResult:
    """
    Автоматично виправляє деякі проблеми графа:
      - видаляє ребра, що входять до нульових циклів;
      - видаляє ізольовані вузли з явних вузлів.
    Записує операцію у GraphFixLog.
    """

    # Які ребра видаляти: всі (u,v), що належать хоча б одному циклу
    edges_to_remove: Set[Tuple[int, int]] = set()
    for cycle in quality.zero_weight_cycles:
        if not cycle:
            continue
        # цикл описаний як [n0, n1, ..., nk-1]; ребра n0->n1, ..., n(k-1)->n0
        for i in range(len(cycle)):
            u = cycle[i]
            v = cycle[(i + 1) % len(cycle)]
            edges_to_remove.add((u, v))

    removed_edges = 0
    if edges_to_remove:
        removed_edges = manager.remove_edges(edges_to_remove)

    removed_isolated = 0
    if quality.isolated_nodes:
        removed_isolated = manager.remove_isolated_nodes(quality.isolated_nodes)

    # Логування виправлення
    details = {
        "removed_zero_weight_edges": [
            {"from": u, "to": v} for (u, v) in sorted(edges_to_remove)
        ],
        "isolated_nodes_removed": quality.isolated_nodes,
    }

    log = GraphFixLog(
        fix_type="graph_quality_auto_fix",
        description="Автоматичне видалення нульових циклів та ізольованих вузлів",
        details=json.dumps(details, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return GraphQualityFixResult(
        removed_zero_weight_edges=removed_edges,
        removed_isolated_nodes=removed_isolated,
        log_id=log.id,
    )
