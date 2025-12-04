from __future__ import annotations

import threading
from typing import List, Optional, Set, Tuple

try:
    import routing_core  # type: ignore
except ImportError as e:  # pragma: no cover - handled at runtime
    routing_core = None
    _import_error: Optional[ImportError] = e
else:
    _import_error = None


class GraphManager:
    """
    Обгортка над routing_core.PyGraph + локальний стан графа.
    """

    def __init__(self) -> None:
        if routing_core is None:
            raise RuntimeError(
                "routing_core не встановлено. Запустіть `pip install -e core` "
                "або `maturin develop` у каталозі core (у тій самій venv)."
            )

        self._graph = routing_core.PyGraph()
        self._lock = threading.Lock()

        # Список базових ребер
        self._edges: List[Tuple[int, int, float]] = []

        # Вузли з ребер
        self._edge_nodes: Set[int] = set()

        # Явно додані вузли
        self._explicit_nodes: Set[int] = set()

    # --- Ноди ---

    def add_node(self, node_id: int) -> None:
        with self._lock:
            self._explicit_nodes.add(node_id)

    def get_nodes(self) -> Set[int]:
        with self._lock:
            return set(self._edge_nodes | self._explicit_nodes)

    # --- Ребра ---

    def add_edge(self, from_node: int, to_node: int, weight: float) -> None:
        with self._lock:
            self._graph.add_edge(from_node, to_node, weight)
            self._edges.append((from_node, to_node, weight))
            self._edge_nodes.add(from_node)
            self._edge_nodes.add(to_node)

    def add_edges(self, edges: List[Tuple[int, int, float]]) -> None:
        with self._lock:
            for from_node, to_node, weight in edges:
                self._graph.add_edge(from_node, to_node, weight)
                self._edges.append((from_node, to_node, weight))
                self._edge_nodes.add(from_node)
                self._edge_nodes.add(to_node)

    def get_edges(self) -> List[Tuple[int, int, float]]:
        with self._lock:
            return list(self._edges)

    def _rebuild_core_graph(self) -> None:
        self._graph = routing_core.PyGraph()
        for from_node, to_node, weight in self._edges:
            self._graph.add_edge(from_node, to_node, weight)

    def remove_edges(self, edges_to_remove: Set[Tuple[int, int]]) -> int:
        with self._lock:
            old_edges = self._edges
            self._edges = [
                (u, v, w)
                for (u, v, w) in old_edges
                if (u, v) not in edges_to_remove
            ]
            removed = len(old_edges) - len(self._edges)

            self._edge_nodes = set()
            for u, v, _ in self._edges:
                self._edge_nodes.add(u)
                self._edge_nodes.add(v)

            self._rebuild_core_graph()
            return removed

    def remove_isolated_nodes(self, nodes: List[int]) -> int:
        with self._lock:
            before = len(self._explicit_nodes)
            for n in nodes:
                self._explicit_nodes.discard(n)
            after = len(self._explicit_nodes)
            return before - after

    # --- Статистика ---

    def stats(self) -> Tuple[int, int]:
        with self._lock:
            node_count = len(self._edge_nodes | self._explicit_nodes)
            edge_count = len(self._edges)
            return node_count, edge_count

    # --- Алгоритми пошуку ---

    def shortest_path_dijkstra(self, source: int, target: int):
        distance, path = self._graph.shortest_path_dijkstra(source, target)
        return float(distance), list(path)

    def shortest_path_a_star(self, source: int, target: int):
        distance, path = self._graph.shortest_path_a_star(source, target)
        return float(distance), list(path)

    def shortest_path(self, source: int, target: int):
        distance, path = self._graph.shortest_path(source, target)
        return float(distance), list(path)

    def shortest_paths_batch(self, queries: List[Tuple[int, int]]):
        results = self._graph.shortest_paths_batch(queries)
        return [(float(d), list(p)) for d, p in results]


_graph_manager: Optional[GraphManager] = None


def get_or_create_graph_manager() -> GraphManager:
    """Лінива ініціалізація GraphManager.

    Якщо Rust-модуль не зібрано, повертаємо зрозуміле виключення замість
    неочікуваного ImportError при старті сервера.
    """

    global _graph_manager

    if _graph_manager is not None:
        return _graph_manager

    if _import_error is not None:
        raise RuntimeError(
            "routing_core не встановлено. Запустіть `pip install -e core` "
            "або `maturin develop` у каталозі core (у тій самій venv)."
        )

    _graph_manager = GraphManager()
    return _graph_manager
