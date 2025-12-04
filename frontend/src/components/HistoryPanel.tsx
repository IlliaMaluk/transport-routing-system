import React from "react";
import { RouteHistoryItem } from "../api/client";

interface HistoryPanelProps {
  items?: RouteHistoryItem[];
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ items }) => {
  return (
    <div className="panel">
      <h2>Історія запитів</h2>
      {!items || items.length === 0 ? (
        <p>Ще не виконувалося жодного запиту.</p>
      ) : (
        <ul
          style={{
            listStyle: "none",
            paddingLeft: 0,
            margin: 0,
            maxHeight: "260px",
            overflowY: "auto"
          }}
        >
          {items.map(item => {
            const date = new Date(item.created_at);
            const ts = isNaN(date.getTime())
              ? item.created_at
              : date.toLocaleString();
            return (
              <li
                key={item.id}
                style={{
                  padding: "0.4rem 0",
                  borderBottom: "1px solid #e5e7eb",
                  fontSize: "0.85rem"
                }}
              >
                <div>
                  <strong>
                    {item.source} → {item.target}
                  </strong>{" "}
                  ({item.algorithm}
                  {item.scenario_id != null
                    ? `, сценарій ${item.scenario_id}`
                    : ""})
                </div>
                <div style={{ opacity: 0.8 }}>{ts}</div>
                <div>
                  {item.success ? (
                    <>
                      вага:{" "}
                      {item.total_weight != null
                        ? item.total_weight.toFixed(2)
                        : "N/A"}
                      , час:{" "}
                      {item.execution_time_ms != null
                        ? item.execution_time_ms.toFixed(2) + " ms"
                        : "N/A"}
                    </>
                  ) : (
                    <span style={{ color: "#b91c1c" }}>
                      помилка: {item.error_message}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
