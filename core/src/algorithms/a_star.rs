use std::cmp::Ordering;
use std::collections::BinaryHeap;

use rayon::prelude::*;

use crate::graph::Graph;
use super::PathResult;

#[derive(Copy, Clone, Debug)]
struct State {
    f_cost: f64,
    position: u32,
}

impl Eq for State {}

impl PartialEq for State {
    fn eq(&self, other: &Self) -> bool {
        self.f_cost == other.f_cost && self.position == other.position
    }
}

impl Ord for State {
    fn cmp(&self, other: &Self) -> Ordering {
        // мін-куча через інверсію
        other
            .f_cost
            .partial_cmp(&self.f_cost)
            .unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// A* між source і target.
/// Зараз евристика в Graph завжди 0.0 → за поведінкою ≈ Dijkstra.
/// Пізніше можна додати координати та реальну евристику.
pub fn a_star(graph: &Graph, source: u32, target: u32) -> (f64, Vec<u32>) {
    let n = graph.node_count();
    if source as usize >= n || target as usize >= n {
        return (f64::INFINITY, Vec::new());
    }

    let mut g_score = vec![f64::INFINITY; n];
    let mut prev: Vec<Option<u32>> = vec![None; n];

    let mut heap = BinaryHeap::new();

    g_score[source as usize] = 0.0;
    let h0 = graph.heuristic(source, target);
    heap.push(State {
        f_cost: h0,
        position: source,
    });

    while let Some(State { f_cost: _f, position }) = heap.pop() {
        if position == target {
            break;
        }

        let current_g = g_score[position as usize];
        if !current_g.is_finite() {
            continue;
        }

        for edge in graph.neighbors(position) {
            let tentative_g = current_g + edge.weight;
            let idx = edge.to as usize;

            if tentative_g < g_score[idx] {
                g_score[idx] = tentative_g;
                prev[idx] = Some(position);
                let f_cost = tentative_g + graph.heuristic(edge.to, target);
                heap.push(State {
                    f_cost,
                    position: edge.to,
                });
            }
        }
    }

    let d = g_score[target as usize];
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

/// Паралельний A* для набору запитів.
pub fn a_star_parallel_batch(graph: &Graph, queries: &[(u32, u32)]) -> Vec<PathResult> {
    queries
        .par_iter()
        .map(|(s, t)| {
            let (d, p) = a_star(graph, *s, *t);
            PathResult { distance: d, path: p }
        })
        .collect()
}
