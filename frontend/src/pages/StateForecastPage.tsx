import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  ForecastHistory,
  ForecastSnapshot,
  KalshiOdds,
  Poll,
  Race,
  RaceIntelligence,
  Simulations,
} from "../api/types";
import { ForecastNeedle } from "../components/ForecastNeedle";
import { InfoButton } from "../components/InfoButton";
import { ForecastHistoryChart } from "../components/ForecastHistoryChart";
import { WinProbabilityHistoryChart } from "../components/WinProbabilityHistoryChart";
import { PollTrendChart } from "../components/PollTrendChart";
import { SimulationHistograms } from "../components/SimulationHistograms";
import { PollTable } from "../components/PollTable";
import { KalshiOddsCard } from "../components/KalshiOddsCard";
import { NewsHeadlinesCard } from "../components/NewsHeadlinesCard";
import { AIMarketAnalysisCard } from "../components/AIMarketAnalysisCard";

const NAV_HEIGHT_PX = 52;

function Card({
  id,
  title,
  children,
}: {
  id?: string;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="glass-panel rounded-lg p-5"
      style={{ scrollMarginTop: NAV_HEIGHT_PX + 12 }}
    >
      {title && (
        <h2
          className="font-title mb-4 text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {title}
        </h2>
      )}
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
  const [raceIntelligence, setRaceIntelligence] = useState<RaceIntelligence | null>(null);
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
        setRaceIntelligence(await api.getRaceIntelligence(stateCode));
      } catch {
        setRaceIntelligence(null);
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
      <div
        className="mx-auto max-w-5xl px-4 py-8"
        style={{ color: "var(--text-secondary)" }}
      >
        <Link
          to="/"
          className="text-sm underline"
          style={{ color: "var(--text-muted)" }}
        >
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
    { id: "forecast-history", label: "Forecast History", visible: !!history },
    {
      id: "win-probability-history",
      label: "Win Probability History",
      visible: !!history,
    },
    { id: "polling-trend", label: "Polling Trend", visible: !!polls },
    {
      id: "simulation-distribution",
      label: "Simulations",
      visible: !!simulations,
    },
    { id: "latest-polls", label: "Latest Polls", visible: !!polls },
    { id: "latest-news", label: "Latest News", visible: !!raceIntelligence },
    { id: "kalshi-odds", label: "Prediction Markets", visible: kalshiOdds.length > 0 },
    { id: "ai-market-analysis", label: "AI Market Analysis", visible: !!raceIntelligence },
  ].filter((s) => s.visible);

  return (
    <div style={{ color: "var(--text-secondary)" }}>
      <nav
        className="sticky top-0 z-20 border-b text-sm"
        style={{
          borderColor: "var(--border)",
          backgroundColor: "var(--page)",
        }}
      >
        <div className="relative flex items-center px-4 py-2" style={{ minHeight: NAV_HEIGHT_PX }}>
          <Link
            to="/"
            className="absolute left-4 inline-flex flex-shrink-0 items-center gap-1 rounded-md px-2.5 py-1.5 underline"
            style={{ color: "var(--text-muted)" }}
          >
            ← Back to map
          </Link>
          {sections.length > 1 && (
            <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-center gap-x-1 gap-y-1">
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
        </div>
      </nav>

      <div className="mx-auto max-w-5xl px-4 py-8">
        <header className="mb-8 mt-2 text-center">
          <h1
            className="font-title text-4xl font-semibold sm:text-5xl"
            style={{ color: "var(--text-primary)" }}
          >
            {race
              ? `${new Date(race.election_date + "T00:00:00").getFullYear()} ${race.state_name} ${race.office} Forecast`
              : "Loading forecast…"}
          </h1>
        </header>
        <InfoButton />

        {error && (
          <div
            className="mb-6 rounded-md border p-3 text-sm"
            style={{
              borderColor: "var(--party-republican)",
              color: "var(--party-republican)",
            }}
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
                No forecast available yet. The server generates one
                automatically on startup and refreshes it as new polls are
                ingested.
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

          {(raceIntelligence || kalshiOdds.length > 0) && (
            <div className="mt-4 flex flex-col gap-6">
              <div className="flex items-center gap-3">
                <div className="h-px flex-1" style={{ backgroundColor: "var(--border)" }} />
                <h2
                  className="font-title text-lg font-semibold uppercase tracking-wide"
                  style={{ color: "var(--text-muted)" }}
                >
                  Race Intelligence
                </h2>
                <div className="h-px flex-1" style={{ backgroundColor: "var(--border)" }} />
              </div>
              <p className="-mt-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
                Context for the forecast above — news and market sentiment. Not part of the model itself.
              </p>

              {raceIntelligence && (
                <Card id="latest-news" title="Latest news">
                  <NewsHeadlinesCard articles={raceIntelligence.news_articles} />
                </Card>
              )}

              {kalshiOdds.length > 0 && (
                <Card id="kalshi-odds">
                  <KalshiOddsCard odds={kalshiOdds} />
                </Card>
              )}

              {raceIntelligence && (
                <Card id="ai-market-analysis" title="AI market analysis">
                  <AIMarketAnalysisCard
                    analysis={raceIntelligence.market_analysis}
                    generatedAt={raceIntelligence.market_analysis_generated_at}
                  />
                </Card>
              )}
            </div>
          )}

          {forecast && (
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Snapshot #{forecast.id} · {forecast.n_polls_used} polls used ·
              method {forecast.method_version} · generated{" "}
              {new Date(forecast.created_at).toLocaleString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
