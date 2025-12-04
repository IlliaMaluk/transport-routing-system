export type OptimizationCriterion = "time" | "distance" | "cost" | "transfers";
export type AlgorithmType = "dijkstra" | "a_star";

export interface EdgeCreate {
  from_node: number;
  to_node: number;
  weight: number;
}

export interface EdgeBulkCreateRequest {
  edges: EdgeCreate[];
}

export interface GraphInfoResponse {
  node_count: number;
  edge_count: number;
}

export interface RouteRequest {
  source: number;
  target: number;
  criteria: OptimizationCriterion[];
  profile?: string | null;
  algorithm?: AlgorithmType; // якщо не вказати — бекенд візьме dijkstra
  scenario_id?: number | null;
}

export interface RouteSegment {
  from_node: number;
  to_node: number;
  weight: number;
}

export interface RouteResponse {
  total_weight: number;
  nodes: number[];
  segments: RouteSegment[];
  algorithm: string;
  execution_time_ms: number;
}

export interface RouteBatchRequest {
  queries: RouteRequest[];
}

export interface RouteBatchItem {
  request: RouteRequest;
  response: RouteResponse;
}

// ---------- Історія + статистика ----------

export interface RouteHistoryItem {
  id: number;
  created_at: string; // ISO-час
  source: number;
  target: number;
  algorithm: string;
  criteria: OptimizationCriterion[];
  profile?: string | null;
  total_weight?: number | null;
  execution_time_ms?: number | null;
  success: boolean;
  error_message?: string | null;
  is_batch: boolean;
  batch_group?: string | null;
  scenario_id?: number | null;
}

export interface AlgorithmStats {
  algorithm: string;
  query_count: number;
  avg_execution_ms?: number | null;
  max_execution_ms?: number | null;
}

export interface PerformanceStatsResponse {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  avg_execution_ms?: number | null;
  max_execution_ms?: number | null;
  per_algorithm: AlgorithmStats[];
}

// ---------- Сценарії ----------

export interface ScenarioSummary {
  id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
}

// ---------- Async batch jobs ----------

export type AsyncJobStatusType = "queued" | "running" | "finished" | "failed";

export interface AsyncJobStatus {
  id: string;
  status: AsyncJobStatusType;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  total_queries: number;
  completed_queries: number;
  error_message?: string | null;
  execution_time_ms?: number | null;
  result?: RouteBatchItem[] | null;
}

export interface AsyncJobsMetricsResponse {
  queue_length: number;
  running_jobs: number;
  finished_jobs: number;
  failed_jobs: number;
  avg_job_time_ms?: number | null;
  cpu_usage_percent?: number | null;
  gpu_usage_percent?: number | null;
}

// ---------- Auth типи (для зручності) ----------

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ---------- Базові налаштування клієнта ----------

// ВАЖЛИВО: тут є експорт API_BASE_URL, який очікує AuthContext
export const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

const API_URL = API_BASE_URL;

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem("auth_token", token);
  } else {
    localStorage.removeItem("auth_token");
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token");
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let text = "";
    try {
      text = await res.text();
    } catch {
      // ignore
    }
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

/**
 * Загальний fetch:
 *  - додає базовий URL
 *  - додає Authorization: Bearer <token>, якщо є
 *  - обробляє помилки
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();

  // Використовуємо звичайний об’єкт, а не HeadersInit
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Якщо в options.headers щось передали — додаємо
  if (options.headers) {
    Object.assign(headers, options.headers as Record<string, string>);
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers, // Record<string, string> perfectly підходить під RequestInit["headers"]
  });

  return handleResponse<T>(res);
}

// ---------- API-функції ----------

export async function getGraphInfo(): Promise<GraphInfoResponse> {
  return apiFetch<GraphInfoResponse>("/graph/info", { method: "GET" });
}

export async function addEdges(
  payload: EdgeBulkCreateRequest
): Promise<GraphInfoResponse> {
  return apiFetch<GraphInfoResponse>("/graph/edges", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchRoute(
  req: RouteRequest
): Promise<RouteResponse> {
  return apiFetch<RouteResponse>("/routes", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function fetchRoutesBatch(
  req: RouteBatchRequest
): Promise<RouteBatchItem[]> {
  return apiFetch<RouteBatchItem[]>("/routes/batch", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// Async jobs

export async function submitAsyncBatch(
  req: RouteBatchRequest
): Promise<AsyncJobStatus> {
  return apiFetch<AsyncJobStatus>("/routes/async/submit", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getAsyncJob(jobId: string): Promise<AsyncJobStatus> {
  return apiFetch<AsyncJobStatus>(`/routes/async/${jobId}`, {
    method: "GET",
  });
}

export async function getAsyncMetrics(): Promise<AsyncJobsMetricsResponse> {
  return apiFetch<AsyncJobsMetricsResponse>("/routes/async/metrics", {
    method: "GET",
  });
}

// Статистика / історія / сценарії

export async function getPerformanceStats(): Promise<PerformanceStatsResponse> {
  return apiFetch<PerformanceStatsResponse>("/stats/performance", {
    method: "GET",
  });
}

export async function getRouteHistory(opts?: {
  limit?: number;
  algorithm?: string;
  onlyFailed?: boolean;
}): Promise<RouteHistoryItem[]> {
  const params = new URLSearchParams();
  const limit = opts?.limit ?? 20;
  params.set("limit", String(limit));
  if (opts?.algorithm) {
    params.set("algorithm", opts.algorithm);
  }
  if (opts?.onlyFailed) {
    params.set("only_failed", "true");
  }
  const qs = params.toString();
  const path = qs ? `/history/queries?${qs}` : "/history/queries";
  return apiFetch<RouteHistoryItem[]>(path, { method: "GET" });
}

export async function getScenarios(): Promise<ScenarioSummary[]> {
  return apiFetch<ScenarioSummary[]>("/scenarios", {
    method: "GET",
  });
}