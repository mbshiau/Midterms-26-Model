import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastHistory, ForecastSnapshot, KalshiOdds, Poll, Race, Simulations } from "../api/types";
import { ForecastNeedle } from "../components/ForecastNeedle";
import { InfoButton } from "../components/InfoButton";
import { ForecastHistoryChart } from "../components/ForecastHistoryChart";
import { WinProbabilityHistoryChart } from "../components/WinProbabilityHistoryChart";
import { PollTrendChart } from "../components/PollTrendChart";
import { SimulationHistograms } from "../components/SimulationHistograms";
import { PollTable } from "../components/PollTable";
import { KalshiOddsCard } from "../components/KalshiOddsCard";

const NAV_HEIGHT_PX = 52;

function Card({
  id,
  title,
  children,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="glass-panel rounded-lg p-5"
      style={{ scrollMarginTop: NAV_HEIGHT_PX + 12 }}
    >
      <h2 className="font-title mb-4 text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function StateForecastPage() {
  const { stateCode = "" } = useParams<{ stateCode: string }>();
  const [race, setRace] = useState<Race | null>(null);
  const [polls, setPolls] = useState<Poll[] | null>(null);
  const [forecast, setForecast] = useState<ForecastSnapshot | null>(null);
  const [history, setHistory] = useState<ForecastHistory | null>(null);
  const [simulations, setSimulations] = useState<Simulations | null>(null);
  const [kalshiOdds, setKalshiOdds] = useState<KalshiOdds[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const loadAll = useCallback(async () => {
    setError(null);
    setNotFound(false);
    try {
      const races = await api.getRaces();
      const matchedRace = races.find((r) => r.state_code === stateCode) ?? null;
      if (!matchedRace) {
        setNotFound(true);
        return;
      }
      setRace(matchedRace);

      const pollsData = await api.getPolls(stateCode);
      setPolls(pollsData);

      try {
        setKalshiOdds(await api.getKalshiOdds(stateCode));
      } catch {
        setKalshiOdds([]);
      }

      try {
        const [forecastData, simulationsData, historyData] = await Promise.all([
          api.getForecast(stateCode),
          api.getSimulations(stateCode),
          api.getForecastHistory(stateCode),
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
  }, [stateCode]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  if (notFound) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8" style={{ color: "var(--text-secondary)" }}>
        <Link to="/" className="text-sm underline" style={{ color: "var(--text-muted)" }}>
          ← Back to map
        </Link>
        <p className="mt-4" style={{ color: "var(--text-muted)" }}>
          No forecast model exists for this state yet.
        </p>
      </div>
    );
  }

  const sections = [
    { id: "forecast-summary", label: "Summary", visible: true },
    { id: "forecast-history", label: "Forecast history", visible: !!history },
    { id: "win-probability-history", label: "Win probability history", visible: !!history },
    { id: "polling-trend", label: "Polling trend", visible: !!polls },
    { id: "simulation-distribution", label: "Simulations", visible: !!simulations },
    { id: "latest-polls", label: "Latest polls", visible: !!polls },
    { id: "kalshi-odds", label: "Kalshi odds", visible: kalshiOdds.length > 0 },
  ].filter((s) => s.visible);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8" style={{ color: "var(--text-secondary)" }}>
      <header className="mb-8 mt-2 text-center">
        <h1 className="font-title text-4xl font-semibold sm:text-5xl" style={{ color: "var(--text-primary)" }}>
          {race
            ? `${new Date(race.election_date + "T00:00:00").getFullYear()} ${race.state_name} ${race.office} Forecast`
            : "Loading forecast…"}
        </h1>
      </header>
      <InfoButton />

      <nav
        className="sticky top-0 z-20 mb-6 flex flex-wrap items-center justify-between gap-x-6 gap-y-1 border-b px-1 py-2 text-sm"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--page)", minHeight: NAV_HEIGHT_PX }}
      >
        <Link
          to="/"
          className="inline-flex flex-shrink-0 items-center gap-1 rounded-md px-2.5 py-1.5 underline"
          style={{ color: "var(--text-muted)" }}
        >
          ← Back to map
        </Link>
        {sections.length > 1 && (
          <div className="flex flex-wrap items-center gap-x-1 gap-y-1">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="rounded-md px-2.5 py-1.5 hover:underline"
                style={{ color: "var(--text-secondary)" }}
              >
                {s.label}
              </a>
            ))}
          </div>
        )}
      </nav>

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
          <Card id="forecast-summary" title="Forecast summary">
            <ForecastNeedle results={forecast.results} />
          </Card>
        ) : (
          <Card id="forecast-summary" title="Forecast summary">
            <p style={{ color: "var(--text-muted)" }}>
              No forecast available yet. The server generates one automatically on startup and
              refreshes it as new polls are ingested.
            </p>
          </Card>
        )}

        {history && (
          <Card id="forecast-history" title="Forecast history">
            <ForecastHistoryChart history={history} />
          </Card>
        )}

        {history && (
          <Card id="win-probability-history" title="Win probability history">
            <WinProbabilityHistoryChart history={history} />
          </Card>
        )}

        {polls && race && (
          <Card id="polling-trend" title="Polling trend">
            <PollTrendChart polls={polls} electionDate={race.election_date} />
          </Card>
        )}

        {simulations && (
          <Card
            id="simulation-distribution"
            title={`Simulation distribution (${simulations.n_simulations.toLocaleString()} runs)`}
          >
            <SimulationHistograms histograms={simulations.histograms} />
          </Card>
        )}

        {polls && (
          <Card id="latest-polls" title="Latest polls">
            <PollTable polls={polls} />
          </Card>
        )}

        {kalshiOdds.length > 0 && (
          <Card id="kalshi-odds" title="Kalshi prediction market">
            <KalshiOddsCard odds={kalshiOdds} />
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
