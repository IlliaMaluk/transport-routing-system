import React, { useEffect, useState } from "react";
import {
  GraphInfoResponse,
  RouteBatchItem,
  RouteHistoryItem,
  RouteResponse,
  PerformanceStatsResponse,
  addEdges,
  getGraphInfo,
  getPerformanceStats,
  getRouteHistory,
} from "./api/client";
import { RouteForm } from "./components/RouteForm";
import { BatchRouteForm } from "./components/BatchRouteForm";
import { StatsPanel } from "./components/StatsPanel";
import { MapView } from "./components/MapView";
import { HistoryPanel } from "./components/HistoryPanel";

const App: React.FC = () => {
  const [graphInfo, setGraphInfo] = useState<GraphInfoResponse | undefined>();
  const [currentRoute, setCurrentRoute] = useState<RouteResponse | undefined>();
  const [batchItems, setBatchItems] = useState<RouteBatchItem[] | undefined>();
  const [performance, setPerformance] = useState<PerformanceStatsResponse | undefined>();
  const [historyItems, setHistoryItems] = useState<RouteHistoryItem[] | undefined>();

  const [initializing, setInitializing] = useState<boolean>(false);
  const [initError, setInitError] = useState<string | null>(null);

  const refreshGraphInfo = async () => {
    try {
      const info = await getGraphInfo();
      setGraphInfo(info);
    } catch (err) {
      console.error("Не вдалося отримати інформацію про граф:", err);
    }
  };

  const refreshPerformanceAndHistory = async () => {
    try {
      const [perf, hist] = await Promise.all([
        getPerformanceStats(),
        getRouteHistory({ limit: 30 }),
      ]);
      setPerformance(perf);
      setHistoryItems(hist);
    } catch (err) {
      console.error("Не вдалося оновити статистику/історію:", err);
    }
  };

  const initializeGraphIfEmpty = async () => {
    try {
      setInitializing(true);
      setInitError(null);
      const info = await getGraphInfo();
      setGraphInfo(info);

      if (info.edge_count === 0) {
        const newInfo = await addEdges({
          edges: [
            { from_node: 0, to_node: 1, weight: 5.0 },
            { from_node: 1, to_node: 2, weight: 3.0 },
            { from_node: 2, to_node: 3, weight: 2.0 },
          ],
        });
        setGraphInfo(newInfo);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setInitError(msg);
    } finally {
      setInitializing(false);
    }
  };

  useEffect(() => {
    void (async () => {
      await initializeGraphIfEmpty();
      await refreshPerformanceAndHistory();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRouteLoaded = async (route: RouteResponse) => {
    setCurrentRoute(route);
    await refreshGraphInfo();
    await refreshPerformanceAndHistory();
  };

  const handleBatchResult = async (items: RouteBatchItem[]) => {
    setBatchItems(items);
    await refreshGraphInfo();
    await refreshPerformanceAndHistory();
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="flex justify-between items-center w-full">
          <div>
            <h1>Веб-система визначення оптимального шляху</h1>
            <p className="subtitle">
              Транспортні мережі, паралельний пошук маршрутів (Rust + FastAPI + React)
            </p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="left-column">
          {initError && (
            <div className="error-box">Помилка ініціалізації графа: {initError}</div>
          )}

          <RouteForm onRouteLoaded={handleRouteLoaded} disabled={initializing} />

          <BatchRouteForm onBatchResult={handleBatchResult} disabled={initializing} />

          <StatsPanel
            graphInfo={graphInfo}
            batchItems={batchItems}
            performance={performance}
          />
        </section>

        <section className="right-column">
          <MapView route={currentRoute} />
          {currentRoute && (
            <div className="panel route-details">
              <h2>Поточний маршрут</h2>
              <p>
                Алгоритм: <strong>{currentRoute.algorithm}</strong>
              </p>
              <p>
                Вага: <strong>{currentRoute.total_weight}</strong>
              </p>
              <p>
                Час обчислення: <strong>{currentRoute.execution_time_ms.toFixed(2)} ms</strong>
              </p>
              <p>Шлях: {currentRoute.nodes.join(" → ")}</p>
            </div>
          )}

          <HistoryPanel items={historyItems} />
        </section>
      </main>
    </div>
  );
};

export default App;
