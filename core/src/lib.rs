use pyo3::prelude::*;

mod graph;
mod algorithms;

use graph::Graph;
use algorithms::dijkstra::{dijkstra, dijkstra_parallel_batch};
use algorithms::a_star::{a_star, a_star_parallel_batch};
use algorithms::PathResult;

#[pyclass]
pub struct PyGraph {
    inner: Graph,
}

#[pymethods]
impl PyGraph {
    #[new]
    pub fn new() -> Self {
        PyGraph {
            inner: Graph::new(),
        }
    }

    /// Додати ребро from -> to з вагою weight
    pub fn add_edge(&mut self, from: u32, to: u32, weight: f64) {
        self.inner.add_edge(from, to, weight);
    }

    /// Базовий метод (для сумісності): Dijkstra.
    pub fn shortest_path(&self, source: u32, target: u32) -> PyResult<(f64, Vec<u32>)> {
        let (dist, path) = dijkstra(&self.inner, source, target);
        Ok((dist, path))
    }

    /// Dijkstra явно
    pub fn shortest_path_dijkstra(&self, source: u32, target: u32) -> PyResult<(f64, Vec<u32>)> {
        let (dist, path) = dijkstra(&self.inner, source, target);
        Ok((dist, path))
    }

    /// A* явно
    pub fn shortest_path_a_star(&self, source: u32, target: u32) -> PyResult<(f64, Vec<u32>)> {
        let (dist, path) = a_star(&self.inner, source, target);
        Ok((dist, path))
    }

    /// Пакетний пошук (за замовчуванням Dijkstra)
    pub fn shortest_paths_batch(&self, queries: Vec<(u32, u32)>) -> PyResult<Vec<(f64, Vec<u32>)>> {
        let results: Vec<PathResult> = dijkstra_parallel_batch(&self.inner, &queries);
        Ok(results
            .into_iter()
            .map(|r| (r.distance, r.path))
            .collect())
    }

    pub fn shortest_paths_batch_dijkstra(
        &self,
        queries: Vec<(u32, u32)>,
    ) -> PyResult<Vec<(f64, Vec<u32>)>> {
        let results: Vec<PathResult> = dijkstra_parallel_batch(&self.inner, &queries);
        Ok(results
            .into_iter()
            .map(|r| (r.distance, r.path))
            .collect())
    }

    pub fn shortest_paths_batch_a_star(
        &self,
        queries: Vec<(u32, u32)>,
    ) -> PyResult<Vec<(f64, Vec<u32>)>> {
        let results: Vec<PathResult> = a_star_parallel_batch(&self.inner, &queries);
        Ok(results
            .into_iter()
            .map(|r| (r.distance, r.path))
            .collect())
    }
}

#[pymodule]
fn routing_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyGraph>()?;
    Ok(())
}
