import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastHistory, ForecastSnapshot, Race } from "../api/types";
import { GooeyText, type GooeyTextEntry } from "../components/GooeyText";
import { UsMap } from "../components/UsMap";
import { partyAbbrev, partyColorVar, type ProbabilityTier } from "../lib/partyColor";

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
  history: ForecastHistory | null;
}

interface CandidateMove {
  name: string;
  party: string;
  deltaPts: number;
}

interface Mover {
  stateCode: string;
  stateName: string;
  candidates: CandidateMove[];
  maxAbsDeltaPts: number;
}

// Compares the two most recent forecast snapshots for a race and reports how
// much each candidate's vote share moved between them. Races with fewer than
// two snapshots (nothing to compare against yet) are skipped.
function computeMover(entry: RaceLean): Mover | null {
  const snapshots = entry.history?.snapshots;
  if (!snapshots || snapshots.length < 2 || !entry.forecast) return null;

  const sorted = [...snapshots].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );
  const latest = sorted[sorted.length - 1];
  const previous = sorted[sorted.length - 2];

  const candidates = latest.results
    .map((r) => {
      const priorResult = previous.results.find((p) => p.candidate.id === r.candidate.id);
      if (!priorResult) return null;
      return {
        name: r.candidate.name,
        party: r.candidate.party,
        deltaPts: r.mean_vote_share - priorResult.mean_vote_share,
      };
    })
    .filter((c): c is CandidateMove => c !== null)
    .sort((a, b) => b.deltaPts - a.deltaPts);
  if (candidates.length === 0) return null;

  return {
    stateCode: entry.race.state_code,
    stateName: entry.race.state_name,
    candidates,
    maxAbsDeltaPts: Math.max(...candidates.map((c) => Math.abs(c.deltaPts))),
  };
}

export function MapPage() {
  const navigate = useNavigate();
  const [racesByState, setRacesByState] = useState<Record<string, RaceLean>>({});
  const [moverSearch, setMoverSearch] = useState("");

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
            let history: ForecastHistory | null = null;
            try {
              history = await api.getForecastHistory(race.state_code);
            } catch {
              history = null;
            }
            return [
              race.state_code,
              { race, leadingParty: leader?.candidate.party ?? null, forecast, history },
            ] as const;
          } catch {
            return [
              race.state_code,
              { race, leadingParty: null, forecast: null, history: null },
            ] as const;
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

  const movers = entries
    .map(computeMover)
    .filter((m): m is Mover => m !== null)
    .sort((a, b) => b.maxAbsDeltaPts - a.maxAbsDeltaPts);

  const moverQuery = moverSearch.trim().toLowerCase();
  const filteredMovers = moverQuery
    ? movers.filter(
        (m) =>
          m.stateName.toLowerCase().includes(moverQuery) ||
          m.candidates.some((c) => c.name.toLowerCase().includes(moverQuery))
      )
    : movers;

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
              <span style={{ color: "var(--text-secondary)" }}>No election</span>
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
            if (!entry?.forecast) return null;

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

      <section className="glass-panel mt-6 rounded-lg p-5">
        <h2 className="font-title mb-4 text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Biggest movers since last refresh
        </h2>
        {movers.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>
            Not enough forecast history yet to show movement — check back after the next refresh.
          </p>
        ) : (
          <>
            <input
              type="text"
              value={moverSearch}
              onChange={(e) => setMoverSearch(e.target.value)}
              placeholder="Search states or candidates"
              className="mb-4 w-full rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--border)",
                backgroundColor: "var(--surface)",
                color: "var(--text-primary)",
              }}
            />
            {filteredMovers.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No states match “{moverSearch}”.</p>
            ) : (
              <div className="max-h-[620px] overflow-y-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr
                      className="sticky top-0 text-left"
                      style={{ backgroundColor: "var(--surface)" }}
                    >
                      <th
                        className="w-2/5 border-b py-2 pr-4 pl-12 text-left font-medium"
                        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                      >
                        State
                      </th>
                      <th
                        className="w-2/5 border-b py-2 pr-4 pl-4 text-left font-medium"
                        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                      >
                        Candidates
                      </th>
                      <th
                        className="border-b py-2 pl-4 text-left font-medium"
                        style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
                      >
                        Shift
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMovers.map((m) => (
                      <tr
                        key={m.stateCode}
                        onClick={() => navigate(`/states/${m.stateCode}`)}
                        className="cursor-pointer border-b transition-opacity hover:opacity-70"
                        style={{ borderColor: "var(--border)" }}
                      >
                        <td
                          className="py-3 pr-4 pl-12 align-top font-medium"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {m.stateName}
                        </td>
                        <td className="py-3 pr-4 pl-4 align-top">
                          <div className="flex flex-col gap-1.5">
                            {m.candidates.map((c) => (
                              <span key={c.name} style={{ color: "var(--text-secondary)" }}>
                                {c.name}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 pl-4 align-top">
                          <div className="flex flex-col gap-1.5">
                            {m.candidates.map((c) => (
                              <span
                                key={c.name}
                                className="font-semibold tabular-nums"
                                style={{ color: partyColorVar(c.party) }}
                              >
                                {partyAbbrev(c.party)} {c.deltaPts >= 0 ? "▲" : "▼"}{" "}
                                {Math.abs(c.deltaPts).toFixed(1)} pts
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
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
