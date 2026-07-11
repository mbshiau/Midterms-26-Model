import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastSnapshot, Race } from "../api/types";
import { UsMap } from "../components/UsMap";
import type { ProbabilityTier } from "../lib/partyColor";

const TIER_LABELS: { tier: ProbabilityTier; label: string }[] = [
  { tier: 95, label: "95%+" },
  { tier: 75, label: "75-95%" },
  { tier: 60, label: "60-75%" },
  { tier: 50, label: "50-60%" },
];

function TierSwatch({ slug, tier }: { slug: "democratic" | "republican"; tier: ProbabilityTier }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5 rounded-full"
      style={{ backgroundColor: `var(--party-${slug}-${tier})` }}
    />
  );
}

interface RaceLean {
  race: Race;
  leadingParty: string | null;
  forecast: ForecastSnapshot | null;
}

export function MapPage() {
  const navigate = useNavigate();
  const [racesByState, setRacesByState] = useState<Record<string, RaceLean>>({});

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const races = await api.getRaces();
      if (cancelled) return;

      const entries = await Promise.all(
        races.map(async (race) => {
          try {
            const forecast = await api.getForecast(race.state_code);
            const leader = [...forecast.results].sort(
              (a, b) => b.mean_vote_share - a.mean_vote_share
            )[0];
            return [
              race.state_code,
              { race, leadingParty: leader?.candidate.party ?? null, forecast },
            ] as const;
          } catch {
            return [race.state_code, { race, leadingParty: null, forecast: null }] as const;
          }
        })
      );

      if (!cancelled) setRacesByState(Object.fromEntries(entries));
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const availableStateNames = Object.values(racesByState)
    .map((r) => r.race.state_name)
    .sort();

  const entries = Object.values(racesByState);
  const demCount = entries.filter((r) => r.leadingParty === "Democratic").length;
  const repCount = entries.filter((r) => r.leadingParty === "Republican").length;
  const lastUpdated = entries
    .map((r) => r.forecast?.created_at)
    .filter((ts): ts is string => Boolean(ts))
    .map((ts) => new Date(ts).getTime())
    .reduce((max, ts) => Math.max(max, ts), 0);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8" style={{ color: "var(--text-secondary)"}}>
      <header className="mb-8 text-center">
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          2026 Governor Race Forecasts
        </h1>
        {entries.length > 0 && (
          <p className="mt-1 text-sm">
            <span style={{ color: "var(--party-democratic)" }}>Democrats favored in {demCount} state{demCount === 1 ? "" : "s"}</span>
            {" · "}
            <span style={{ color: "var(--party-republican)" }}>Republicans favored in {repCount} state{repCount === 1 ? "" : "s"}</span>
          </p>
        )}
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Click a state to view its forecast.{" "}
          {availableStateNames.length > 0
            ? `Models built so far: ${availableStateNames.join(", ")}.`
            : "Loading available states…"}
        </p>
        {lastUpdated > 0 && (
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            Model last updated {new Date(lastUpdated).toLocaleString()}
          </p>
        )}
      </header>

      <section
        className="rounded-lg border p-5"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
      >
        <UsMap
          getVisual={(id) => {
            const entry = racesByState[id];
            if (!entry?.forecast) return null;

            const winner = [...entry.forecast.results].sort(
              (a, b) => b.win_probability - a.win_probability
            )[0];
            if (!winner) return null;

            return {
              party: winner.candidate.party,
              winProbability: winner.win_probability,
              isFlip: winner.candidate.party !== entry.race.current_holder_party,
            };
          }}
          isClickable={(id) => id in racesByState}
          onStateClick={(id) => {
            if (id in racesByState) navigate(`/states/${id}`);
          }}
          getTooltip={(id) => {
            const entry = racesByState[id];
            if (!entry) return { comingSoon: true };
            if (!entry.forecast) return null;

            const sorted = [...entry.forecast.results].sort(
              (a, b) => b.mean_vote_share - a.mean_vote_share
            );
            const winner = sorted[0];

            return {
              candidates: sorted.map((r) => ({
                name: r.candidate.name,
                party: r.candidate.party,
                voteShare: r.mean_vote_share,
              })),
              winner: winner
                ? {
                    name: winner.candidate.name,
                    party: winner.candidate.party,
                    probability: winner.win_probability,
                  }
                : null,
            };
          }}
        />

        <div className="mt-4 flex flex-col gap-3 text-sm">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <span className="font-medium" style={{ color: "var(--text-secondary)" }}>
              Win probability:
            </span>
            {TIER_LABELS.map(({ tier, label }) => (
              <span key={`d-${tier}`} className="flex items-center gap-1.5">
                <TierSwatch slug="democratic" tier={tier} />
                <span style={{ color: "var(--text-muted)" }}>{label}</span>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <span className="font-medium opacity-0" style={{ color: "var(--text-secondary)" }} aria-hidden>
              Win probability:
            </span>
            {TIER_LABELS.map(({ tier, label }) => (
              <span key={`r-${tier}`} className="flex items-center gap-1.5">
                <TierSwatch slug="republican" tier={tier} />
                <span style={{ color: "var(--text-muted)" }}>{label}</span>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t pt-3" style={{ borderColor: "var(--border)" }}>
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{
                  background:
                    "repeating-linear-gradient(45deg, var(--party-democratic-75), var(--party-democratic-75) 2px, var(--surface) 2px, var(--surface) 4px)",
                }}
              />
              <span style={{ color: "var(--text-secondary)" }}>Projected flip</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "var(--gridline)" }} />
              <span style={{ color: "var(--text-secondary)" }}>Coming soon</span>
            </span>
          </div>
        </div>
      </section>

      <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
        Map data from{" "}
        <a
          href="https://github.com/VictorCazanave/svg-maps/tree/master/packages/usa"
          target="_blank"
          rel="noreferrer"
          className="underline"
        >
          @svg-maps/usa
        </a>{" "}
        (based on amCharts), used under CC BY-NC 4.0.
      </p>
    </div>
  );
}
