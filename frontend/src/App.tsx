import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { ForecastHistory, ForecastSnapshot, Poll, Simulations } from "./api/types";
import { ForecastSummary } from "./components/ForecastSummary";
import { WinProbabilityMeter } from "./components/WinProbabilityMeter";
import { ModelCompositionCard } from "./components/ModelCompositionCard";
import { ForecastHistoryChart } from "./components/ForecastHistoryChart";
import { WinProbabilityHistoryChart } from "./components/WinProbabilityHistoryChart";
import { PollTrendChart } from "./components/PollTrendChart";
import { SimulationHistograms } from "./components/SimulationHistograms";
import { PollTable } from "./components/PollTable";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="rounded-lg border p-5"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
    >
      <h2 className="mb-4 text-base font-semibold" style={{ color: "var(--text-primary)" }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

function App() {
  const [polls, setPolls] = useState<Poll[] | null>(null);
  const [forecast, setForecast] = useState<ForecastSnapshot | null>(null);
  const [history, setHistory] = useState<ForecastHistory | null>(null);
  const [simulations, setSimulations] = useState<Simulations | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setError(null);
    try {
      const pollsData = await api.getPolls();
      setPolls(pollsData);

      try {
        const [forecastData, simulationsData, historyData] = await Promise.all([
          api.getForecast(),
          api.getSimulations(),
          api.getForecastHistory(),
        ]);
        setForecast(forecastData);
        setSimulations(simulationsData);
        setHistory(historyData);
      } catch {
        // Server hasn't generated a forecast yet (e.g. fresh DB, no polls).
        // The forecast is produced once by the server on startup and
        // refreshed automatically as new polls come in — never from here.
        setForecast(null);
        setSimulations(null);
        setHistory(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8" style={{ color: "var(--text-secondary)" }}>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          2026 Pennsylvania Governor Forecast
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Josh Shapiro (D) vs. Stacy Garrity (R) — Monte Carlo simulation blending weighted polling
          averages with a fundamentals model
        </p>
      </header>

      {error && (
        <div
          className="mb-6 rounded-md border p-3 text-sm"
          style={{ borderColor: "var(--party-republican)", color: "var(--party-republican)" }}
        >
          {error}
        </div>
      )}

      <div className="flex flex-col gap-6">
        {forecast ? (
          <Card title="Forecast summary">
            <ForecastSummary results={forecast.results} />
          </Card>
        ) : (
          <Card title="Forecast summary">
            <p style={{ color: "var(--text-muted)" }}>
              No forecast available yet. The server generates one automatically on startup and
              refreshes it as new polls are ingested.
            </p>
          </Card>
        )}

        {forecast && (
          <Card title="Win probability">
            <WinProbabilityMeter results={forecast.results} />
          </Card>
        )}

        {forecast && (
          <Card title="Model composition: polls + fundamentals">
            <ModelCompositionCard forecast={forecast} />
          </Card>
        )}

        {history && (
          <Card title="Forecast history vs. actual result">
            <ForecastHistoryChart history={history} />
          </Card>
        )}

        {history && (
          <Card title="Win probability history">
            <WinProbabilityHistoryChart history={history} />
          </Card>
        )}

        {polls && (
          <Card title="Polling trend">
            <PollTrendChart polls={polls} />
          </Card>
        )}

        {simulations && (
          <Card title={`Simulation distribution (${simulations.n_simulations.toLocaleString()} runs)`}>
            <SimulationHistograms histograms={simulations.histograms} />
          </Card>
        )}

        {polls && (
          <Card title="Latest polls">
            <PollTable polls={polls} />
          </Card>
        )}

        {forecast && (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Snapshot #{forecast.id} · {forecast.n_polls_used} polls used · method{" "}
            {forecast.method_version} · generated{" "}
            {new Date(forecast.created_at).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
}

export default App;
