import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Race } from "../api/types";
import { UsMap } from "../components/UsMap";
import { partyColorVar } from "../lib/partyColor";

interface RaceLean {
  race: Race;
  leadingParty: string | null;
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
            return [race.state_code, { race, leadingParty: leader?.candidate.party ?? null }] as const;
          } catch {
            return [race.state_code, { race, leadingParty: null }] as const;
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

  return (
    <div className="mx-auto max-w-4xl px-4 py-8" style={{ color: "var(--text-secondary)" }}>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          2026 Governor Race Forecasts
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Click a state to view its forecast.{" "}
          {availableStateNames.length > 0
            ? `Models built so far: ${availableStateNames.join(", ")}.`
            : "Loading available states…"}
        </p>
      </header>

      <section
        className="rounded-lg border p-5"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
      >
        <UsMap
          getFill={(id) => {
            const entry = racesByState[id];
            if (!entry) return "var(--gridline)";
            return entry.leadingParty ? partyColorVar(entry.leadingParty) : "var(--text-muted)";
          }}
          isClickable={(id) => id in racesByState}
          onStateClick={(id) => {
            if (id in racesByState) navigate(`/states/${id}`);
          }}
        />

        <div className="mt-4 flex flex-wrap items-center gap-6 text-sm">
          <span className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: "var(--party-democratic)" }}
            />
            <span style={{ color: "var(--text-secondary)" }}>Democrat favored</span>
          </span>
          <span className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: "var(--party-republican)" }}
            />
            <span style={{ color: "var(--text-secondary)" }}>Republican favored</span>
          </span>
          <span className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "var(--gridline)" }} />
            <span style={{ color: "var(--text-secondary)" }}>Coming soon</span>
          </span>
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
