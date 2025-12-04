use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Edge {
    pub to: u32,
    pub weight: f64,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Graph {
    adjacency: Vec<Vec<Edge>>,
}

impl Graph {
    /// Створюємо порожній граф
    pub fn new() -> Self {
        Graph {
            adjacency: Vec::new(),
        }
    }

    /// Гарантуємо, що вузол з індексом `node` існує
    pub fn ensure_node(&mut self, node: u32) {
        let idx = node as usize;
        if idx >= self.adjacency.len() {
            self.adjacency.resize_with(idx + 1, Vec::new);
        }
    }

    /// Додаємо орієнтоване ребро from -> to з вагою weight
    pub fn add_edge(&mut self, from: u32, to: u32, weight: f64) {
        self.ensure_node(from);
        self.ensure_node(to);
        self.adjacency[from as usize].push(Edge { to, weight });
    }

    /// Кількість вузлів у графі
    pub fn node_count(&self) -> usize {
        self.adjacency.len()
    }

    /// Сусіди вузла
    pub fn neighbors(&self, node: u32) -> &[Edge] {
        &self.adjacency[node as usize]
    }

    /// Евристика для A*: оцінка "відстані" від node до target.
    /// Поки що завжди 0.0 → A* поводиться як Dijkstra.
    /// Пізніше можна додати координати вузлів та справжню евристику.
    pub fn heuristic(&self, _node: u32, _target: u32) -> f64 {
        0.0
    }
}
