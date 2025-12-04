pub mod dijkstra;
pub mod a_star;

/// Результат знаходження шляху — спільний для різних алгоритмів.
#[derive(Clone, Debug)]
pub struct PathResult {
    pub distance: f64,
    pub path: Vec<u32>,
}
