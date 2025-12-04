use std::cmp::Ordering;
use std::collections::BinaryHeap;

use rayon::prelude::*;

use crate::graph::Graph;
use super::PathResult;

#[derive(Copy, Clone, Debug)]
struct State {
    cost: f64,
    position: u32,
}

// Для BinaryHeap (мін-куча через інверсію порівняння)
impl Eq for State {}

impl PartialEq for State {
    fn eq(&self, other: &Self) -> bool {
        self.cost == other.cost && self.position == other.position
    }
}

impl Ord for State {
    fn cmp(&self, other: &Self) -> Ordering {
        // Інверсія, тому що BinaryHeap у Rust – макс-куча
        other
            .cost
            .partial_cmp(&self.cost)
            .unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Класичний Dijkstra від source до target.
/// Повертає (відстань, шлях).
pub fn dijkstra(graph: &Graph, source: u32, target: u32) -> (f64, Vec<u32>) {
    let n = graph.node_count();
    if source as usize >= n || target as usize >= n {
        return (f64::INFINITY, Vec::new());
    }

    let mut dist = vec![f64::INFINITY; n];
    let mut prev: Vec<Option<u32>> = vec![None; n];

    let mut heap = BinaryHeap::new();

    dist[source as usize] = 0.0;
    heap.push(State {
        cost: 0.0,
        position: source,
    });

    while let Some(State { cost, position }) = heap.pop() {
        if cost > dist[position as usize] {
            continue;
        }

        if position == target {
            break;
        }

        for edge in graph.neighbors(position) {
            let next_cost = cost + edge.weight;
            let next_pos = edge.to;

            if next_cost < dist[next_pos as usize] {
                dist[next_pos as usize] = next_cost;
                prev[next_pos as usize] = Some(position);
                heap.push(State {
                    cost: next_cost,
                    position: next_pos,
                });
            }
        }
    }

    let d = dist[target as usize];
    if !d.is_finite() {
        return (f64::INFINITY, Vec::new());
    }

    // Відновлення шляху
    let mut path = Vec::new();
    let mut current = target;
    path.push(current);
    while let Some(p) = prev[current as usize] {
        current = p;
        path.push(current);
    }
    path.reverse();

    (d, path)
}

/// Паралельний Dijkstra для набору (source, target)-пар.
/// Кожний Dijkstra – послідовний, але запити виконуються паралельно.
pub fn dijkstra_parallel_batch(graph: &Graph, queries: &[(u32, u32)]) -> Vec<PathResult> {
    queries
        .par_iter()
        .map(|(s, t)| {
            let (d, p) = dijkstra(graph, *s, *t);
            PathResult { distance: d, path: p }
        })
        .collect()
}
