import React from "react";
import {
  GraphInfoResponse,
  RouteBatchItem,
  PerformanceStatsResponse
} from "../api/client";

interface StatsPanelProps {
  graphInfo?: GraphInfoResponse;
  batchItems?: RouteBatchItem[];
  performance?: PerformanceStatsResponse;
}

export const StatsPanel: React.FC<StatsPanelProps> = ({
  graphInfo,
  batchItems,
  performance
}) => {
  return (
    <div className="panel block">
      <h2>Статистика</h2>

      {/* Інформація про граф */}
      <h3>Граф</h3>
      {graphInfo ? (
        <ul>
          <li>Кількість вузлів: {graphInfo.node_count}</li>
          <li>Кількість ребер: {graphInfo.edge_count}</li>
        </ul>
      ) : (
        <p>Граф ще не завантажено.</p>
      )}

      {/* Продуктивність */}
      <h3>Продуктивність</h3>
      {performance && performance.total_queries > 0 ? (
        <>
          <ul>
            <li>Всього запитів: {performance.total_queries}</li>
            <li>Успішних: {performance.successful_queries}</li>
            <li>Невдалих: {performance.failed_queries}</li>
            <li>
              Середній час виконання:{" "}
              {performance.avg_execution_ms != null
                ? performance.avg_execution_ms.toFixed(2) + " ms"
                : "N/A"}
            </li>
            <li>
              Макс. час виконання:{" "}
              {performance.max_execution_ms != null
                ? performance.max_execution_ms.toFixed(2) + " ms"
                : "N/A"}
            </li>
          </ul>
          {performance.per_algorithm.length > 0 && (
            <>
              <p style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
                По алгоритмах:
              </p>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: "0.8rem"
                }}
              >
                <thead>
                  <tr>
                    <th style={{ textAlign: "left" }}>Алгоритм</th>
                    <th style={{ textAlign: "right" }}>К-ть</th>
                    <th style={{ textAlign: "right" }}>Avg, ms</th>
                    <th style={{ textAlign: "right" }}>Max, ms</th>
                  </tr>
                </thead>
                <tbody>
                  {performance.per_algorithm.map(item => (
                    <tr key={item.algorithm}>
                      <td>{item.algorithm}</td>
                      <td style={{ textAlign: "right" }}>
                        {item.query_count}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {item.avg_execution_ms != null
                          ? item.avg_execution_ms.toFixed(2)
                          : "N/A"}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {item.max_execution_ms != null
                          ? item.max_execution_ms.toFixed(2)
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      ) : (
        <p>Ще немає даних про продуктивність.</p>
      )}

      {/* Результати batch-пошуку */}
      {batchItems && batchItems.length > 0 && (
        <>
          <h3>Batch-пошук</h3>
          <ul className="batch-results">
            {batchItems.map((item, idx) => (
              <li key={idx}>
                <div>
                  <strong>
                    {item.request.source} → {item.request.target}
                  </strong>
                </div>
                <div>
                  Вага: {item.response.total_weight}, час:{" "}
                  {item.response.execution_time_ms.toFixed(2)} ms
                </div>
                <div>Шлях: {item.response.nodes.join(" → ")}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};
