import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastSnapshot, Race } from "../api/types";
import { GooeyText, type GooeyTextEntry } from "../components/GooeyText";
import { UsMap } from "../components/UsMap";
import type { ProbabilityTier } from "../lib/partyColor";

const TITLE = "2026 Gubernatorial Election Forecast";

const TIER_LABELS: { tier: ProbabilityTier; label: string }[] = [
  { tier: 95, label: "95%+" },
  { tier: 75, label: "75-95%" },
  { tier: 60, label: "60-75%" },
  { tier: 50, label: "50-60%" },
];

function TierSwatch({ slug, tier }: { slug: "democratic" | "republican"; tier: ProbabilityTier }) {
  return (
    <span
      className="inline-block h-2.5 w-2.5"
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

  // Net governorships projected to change party hands vs. who holds the
  // seat today -- a flip toward each party cancels a flip toward the
  // other, same "isFlip" definition UsMap's tooltip already uses.
  const netDemGovernorships = entries.reduce((net, r) => {
    if (!r.leadingParty) return net;
    if (r.leadingParty === "Democratic" && r.race.current_holder_party === "Republican") return net + 1;
    if (r.leadingParty === "Republican" && r.race.current_holder_party === "Democratic") return net - 1;
    return net;
  }, 0);

  const partyFavoredLine: GooeyTextEntry = [
    { text: `Dems favored in ${demCount}`, color: "var(--party-democratic)" },
    { text: "   ·   " },
    { text: `GOP favored in ${repCount}`, color: "var(--party-republican)" },
  ];
  const netSeatLine: GooeyTextEntry =
    netDemGovernorships > 0
      ? [{
          text: `Projected: Dems net +${netDemGovernorships} governorship${netDemGovernorships === 1 ? "" : "s"}`,
          color: "var(--party-democratic)",
        }]
      : netDemGovernorships < 0
        ? [{
            text: `Projected: GOP net +${-netDemGovernorships} governorship${netDemGovernorships === -1 ? "" : "s"}`,
            color: "var(--party-republican)",
          }]
        : "No net governorship flips";

  return (
    <div className="dashboard-background">
    <div className="mx-auto max-w-4xl px-4 pt-16 pb-8" style={{ color: "var(--text-secondary)"}}>
      <header className="mb-8 text-center">
        {entries.length > 0 ? (
          <GooeyText
            texts={[TITLE, partyFavoredLine, netSeatLine]}
            morphTime={1}
            cooldownTime={2.5}
            className="h-10 sm:h-12 md:h-14"
            textClassName="font-title px-2 text-2xl font-semibold sm:text-4xl md:text-5xl"
          />
        ) : (
          <h1 className="font-title text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
            {TITLE}
          </h1>
        )}
        
        {lastUpdated > 0 && (
          <p className="mt-1 text-base" style={{ color: "black" }}>
            LAST UPDATED: {new Date(lastUpdated).toLocaleString()}
          </p>
        )}
      </header>

      <section className="glass-panel rounded-lg p-5">
        <div className="mb-4 flex flex-col gap-3 text-sm">
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
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b pb-3" style={{ borderColor: "var(--border)" }}>
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5"
                style={{
                  background:
                    "repeating-linear-gradient(45deg, var(--text-primary), var(--text-primary) 2px, var(--surface) 2px, var(--surface) 4px)",
                }}
              />
              <span style={{ color: "var(--text-secondary)" }}>Projected flip</span>
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5" style={{ backgroundColor: "var(--gridline)" }} />
              <span style={{ color: "var(--text-secondary)" }}>Coming soon</span>
            </span>
          </div>
        </div>

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
    </div>
  );
}
