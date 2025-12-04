import React, { useState } from "react";
import {
  fetchRoutesBatch,
  RouteBatchItem,
  RouteBatchRequest,
  RouteRequest
} from "../api/client";

interface BatchRouteFormProps {
  onBatchResult: (items: RouteBatchItem[]) => void;
  disabled?: boolean;
}

interface QueryRow {
  id: number;
  source: string;
  target: string;
}

export const BatchRouteForm: React.FC<BatchRouteFormProps> = ({
  onBatchResult,
  disabled
}) => {
  const [rows, setRows] = useState<QueryRow[]>([
    { id: 1, source: "0", target: "1" },
    { id: 2, source: "1", target: "2" }
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addRow = () => {
    const nextId = rows.length > 0 ? Math.max(...rows.map(r => r.id)) + 1 : 1;
    setRows([...rows, { id: nextId, source: "0", target: "1" }]);
  };

  const updateRow = (id: number, field: "source" | "target", value: string) => {
    setRows(rows.map(r => (r.id === id ? { ...r, [field]: value } : r)));
  };

  const removeRow = (id: number) => {
    setRows(rows.filter(r => r.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || loading) return;

    const queries: RouteRequest[] = [];
    for (const row of rows) {
      const s = Number(row.source);
      const t = Number(row.target);
      if (Number.isNaN(s) || Number.isNaN(t)) {
        setError("Усі source/target мають бути числами");
        return;
      }
      queries.push({
        source: s,
        target: t,
        criteria: ["time"],
        profile: null
      });
    }

    const payload: RouteBatchRequest = { queries };

    try {
      setError(null);
      setLoading(true);
      const result = await fetchRoutesBatch(payload);
      onBatchResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="panel block" onSubmit={handleSubmit}>
      <h2>Паралельний пошук (batch)</h2>

      {rows.map(row => (
        <div className="batch-row" key={row.id}>
          <div className="form-row-inline">
            <label>Source</label>
            <input
              type="number"
              value={row.source}
              onChange={e => updateRow(row.id, "source", e.target.value)}
              disabled={disabled}
            />
          </div>
          <div className="form-row-inline">
            <label>Target</label>
            <input
              type="number"
              value={row.target}
              onChange={e => updateRow(row.id, "target", e.target.value)}
              disabled={disabled}
            />
          </div>
          <button
            type="button"
            onClick={() => removeRow(row.id)}
            disabled={disabled}
          >
            ×
          </button>
        </div>
      ))}

      <div style={{ marginTop: "0.5rem" }}>
        <button type="button" onClick={addRow} disabled={disabled}>
          + Додати запит
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      <button
        type="submit"
        style={{ marginTop: "0.5rem" }}
        disabled={disabled || loading}
      >
        {loading ? "Обчислення..." : "Виконати паралельно"}
      </button>
    </form>
  );
};
