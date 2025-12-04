import React, { useEffect, useState } from "react";
import {
  AlgorithmType,
  RouteRequest,
  RouteResponse,
  ScenarioSummary,
  fetchRoute,
  getScenarios
} from "../api/client";

interface RouteFormProps {
  onRouteLoaded: (route: RouteResponse) => void;
  disabled?: boolean;
}

const defaultSource = 0;
const defaultTarget = 1;

export const RouteForm: React.FC<RouteFormProps> = ({
  onRouteLoaded,
  disabled
}) => {
  const [source, setSource] = useState<string>(String(defaultSource));
  const [target, setTarget] = useState<string>(String(defaultTarget));
  const [criterion, setCriterion] = useState<
    "time" | "distance" | "cost" | "transfers"
  >("time");
  const [profile, setProfile] = useState<string>("");
  const [algorithm, setAlgorithm] = useState<AlgorithmType>("dijkstra");

  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>(""); // "" = базова мережа

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Завантажуємо список сценаріїв
    const loadScenarios = async () => {
      try {
        const list = await getScenarios();
        setScenarios(list);
      } catch (err) {
        console.error("Не вдалося завантажити сценарії:", err);
      }
    };
    void loadScenarios();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || loading) return;

    const src = Number(source);
    const tgt = Number(target);
    if (Number.isNaN(src) || Number.isNaN(tgt)) {
      setError("source та target мають бути цілими числами");
      return;
    }

    const scenarioId =
      selectedScenarioId.trim() === ""
        ? undefined
        : Number(selectedScenarioId);

    if (
      scenarioId !== undefined &&
      (Number.isNaN(scenarioId) || !Number.isFinite(scenarioId))
    ) {
      setError("scenario_id має бути числом або порожнім");
      return;
    }

    const req: RouteRequest = {
      source: src,
      target: tgt,
      criteria: [criterion],
      profile: profile || null,
      algorithm,
      scenario_id: scenarioId
    };

    try {
      setError(null);
      setLoading(true);
      const route = await fetchRoute(req);
      onRouteLoaded(route);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="panel block" onSubmit={handleSubmit}>
      <h2>Пошук маршруту</h2>

      <div className="form-row">
        <label>Source node</label>
        <input
          type="number"
          value={source}
          onChange={e => setSource(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div className="form-row">
        <label>Target node</label>
        <input
          type="number"
          value={target}
          onChange={e => setTarget(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div className="form-row">
        <label>Критерій</label>
        <select
          value={criterion}
          onChange={e =>
            setCriterion(
              e.target.value as "time" | "distance" | "cost" | "transfers"
            )
          }
          disabled={disabled}
        >
          <option value="time">Час</option>
          <option value="distance">Відстань</option>
          <option value="cost">Вартість</option>
          <option value="transfers">Кількість пересадок</option>
        </select>
      </div>

      <div className="form-row">
        <label>Алгоритм</label>
        <select
          value={algorithm}
          onChange={e => setAlgorithm(e.target.value as AlgorithmType)}
          disabled={disabled}
        >
          <option value="dijkstra">Dijkstra</option>
          <option value="a_star">A*</option>
        </select>
      </div>

      <div className="form-row">
        <label>Сценарій</label>
        <select
          value={selectedScenarioId}
          onChange={e => setSelectedScenarioId(e.target.value)}
          disabled={disabled}
        >
          <option value="">Без сценарію (базова мережа)</option>
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>
              {s.name} {s.is_active ? "" : "(неактивний)"}
            </option>
          ))}
        </select>
      </div>

      <div className="form-row">
        <label>Профіль (опц.)</label>
        <input
          type="text"
          placeholder="cargo, public_peak..."
          value={profile}
          onChange={e => setProfile(e.target.value)}
          disabled={disabled}
        />
      </div>

      {error && <div className="error-box">{error}</div>}

      <button type="submit" disabled={disabled || loading}>
        {loading ? "Обчислення..." : "Знайти маршрут"}
      </button>
    </form>
  );
};
