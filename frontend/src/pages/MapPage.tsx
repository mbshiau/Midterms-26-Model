import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { RaceSummary, RaceSummaryDelta } from "../api/types";
import { GooeyText, type GooeyTextEntry } from "../components/GooeyText";
import { UsMap } from "../components/UsMap";
import { partyAbbrev, partyColorVar, type ProbabilityTier } from "../lib/partyColor";

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

type ViewMode = "since-refresh" | "this-week" | "closest";

interface CandidateMetric {
  name: string;
  party: string;
  /** Meaning depends on the active view: a vote-share delta in points for
   * the two "movers" modes, or the current mean vote share for "closest". */
  value: number;
}

interface RaceMetricRow {
  slug: string;
  stateName: string;
  candidates: CandidateMetric[];
  /** Row ordering key for the active view -- callers sort by this before
   * storing the row, since the two movers modes want descending order
   * (biggest shift first) while closest races wants ascending (smallest
   * margin first). */
  sortValue: number;
}

// since_refresh/this_week are already the precomputed vote-share deltas from
// GET /races/summary (see app.services.forecasting.race_movement_summary) --
// the backend picks the right pair of historical snapshots and does the
// diffing, so the map page never has to fetch full forecast history itself.
function deltaRow(entry: RaceSummary, deltas: RaceSummaryDelta[] | null): RaceMetricRow | null {
  if (!deltas || deltas.length === 0) return null;
  return {
    slug: entry.race.slug,
    stateName: entry.race.state_name,
    candidates: deltas.map((d) => ({ name: d.name, party: d.party, value: d.delta })),
    sortValue: Math.max(...deltas.map((d) => Math.abs(d.delta))),
  };
}

function computeSinceRefreshRow(entry: RaceSummary): RaceMetricRow | null {
  return deltaRow(entry, entry.since_refresh);
}

function computeThisWeekRow(entry: RaceSummary): RaceMetricRow | null {
  return deltaRow(entry, entry.this_week);
}

// Current vote share for each candidate, ranked by how close the top two are
// -- the smallest margin is the closest race. entry.candidates is already
// sorted by mean vote share, descending (see race_movement_summary).
function computeClosestRow(entry: RaceSummary): RaceMetricRow | null {
  const sorted = entry.candidates;
  if (sorted.length < 2) return null;
  const margin = sorted[0].mean_vote_share - sorted[1].mean_vote_share;

  return {
    slug: entry.race.slug,
    stateName: entry.race.state_name,
    candidates: sorted.map((r) => ({
      name: r.name,
      party: r.party,
      value: r.mean_vote_share,
    })),
    sortValue: margin,
  };
}

const SECTION_TITLES: Record<ViewMode, string> = {
  "since-refresh": "Biggest movers since last refresh",
  "this-week": "Biggest movers this week",
  closest: "Closest races",
};

const EMPTY_MESSAGES: Record<ViewMode, string> = {
  "since-refresh": "Not enough forecast history yet to show movement — check back after the next refresh.",
  "this-week": "Not enough forecast history yet spanning a full week — check back soon.",
  closest: "No forecasts available yet.",
};

// The map's leading party for a race is whoever has the higher mean vote
// share -- entry.candidates is already sorted that way by the backend (see
// race_movement_summary), so the leader is just the first entry.
function leadingPartyOf(entry: RaceSummary): string | null {
  return entry.candidates[0]?.party ?? null;
}

export function MapPage({ office }: { office: "Governor" | "Senate" }) {
  const navigate = useNavigate();
  const [racesByState, setRacesByState] = useState<Record<string, RaceSummary>>({});
  const [moverSearch, setMoverSearch] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("since-refresh");

  const title = office === "Senate" ? "2026 Senate Election Forecast" : "2026 Gubernatorial Election Forecast";
  const seatNoun = office === "Senate" ? "Senate seat" : "governorship";

  useEffect(() => {
    let cancelled = false;
    setRacesByState({});

    (async () => {
      // Single bulk request instead of an N-race x (/forecast +
      // /forecast/history) fan-out -- see GET /races/summary.
      const summaries = await api.getRaceSummaries(office);
      if (cancelled) return;
      const entries = summaries.map((s) => [s.race.state_code, s] as const);
      setRacesByState(Object.fromEntries(entries));
    })();

    return () => {
      cancelled = true;
    };
  }, [office]);

  const entries = Object.values(racesByState);
  const demCount = entries.filter((r) => leadingPartyOf(r) === "Democratic").length;
  const repCount = entries.filter((r) => leadingPartyOf(r) === "Republican").length;
  const lastUpdated = entries
    .map((r) => r.latest_forecast_created_at)
    .filter((ts): ts is string => Boolean(ts))
    .map((ts) => new Date(ts).getTime())
    .reduce((max, ts) => Math.max(max, ts), 0);

  // Net seats projected to change party hands vs. who holds the seat today
  // -- a flip toward each party cancels a flip toward the other, same
  // "isFlip" definition UsMap's tooltip already uses.
  const netDemSeats = entries.reduce((net, r) => {
    const leadingParty = leadingPartyOf(r);
    if (!leadingParty) return net;
    if (leadingParty === "Democratic" && r.race.current_holder_party === "Republican") return net + 1;
    if (leadingParty === "Republican" && r.race.current_holder_party === "Democratic") return net - 1;
    return net;
  }, 0);

  const partyFavoredLine: GooeyTextEntry = [
    { text: `Dems favored in ${demCount}`, color: "var(--party-democratic)" },
    { text: "   ·   " },
    { text: `GOP favored in ${repCount}`, color: "var(--party-republican)" },
  ];
  const netSeatLine: GooeyTextEntry =
    netDemSeats > 0
      ? [{
          text: `Projected: Dems net +${netDemSeats} ${seatNoun}${netDemSeats === 1 ? "" : "s"}`,
          color: "var(--party-democratic)",
        }]
      : netDemSeats < 0
        ? [{
            text: `Projected: GOP net +${-netDemSeats} ${seatNoun}${netDemSeats === -1 ? "" : "s"}`,
            color: "var(--party-republican)",
          }]
        : `No net ${seatNoun} flips`;

  const sinceRefreshRows = entries
    .map(computeSinceRefreshRow)
    .filter((r): r is RaceMetricRow => r !== null)
    .sort((a, b) => b.sortValue - a.sortValue);
  const thisWeekRows = entries
    .map(computeThisWeekRow)
    .filter((r): r is RaceMetricRow => r !== null)
    .sort((a, b) => b.sortValue - a.sortValue);
  const closestRows = entries
    .map(computeClosestRow)
    .filter((r): r is RaceMetricRow => r !== null)
    .sort((a, b) => a.sortValue - b.sortValue);

  const activeRows =
    viewMode === "since-refresh" ? sinceRefreshRows : viewMode === "this-week" ? thisWeekRows : closestRows;

  const moverQuery = moverSearch.trim().toLowerCase();
  const filteredRows = moverQuery
    ? activeRows.filter(
        (r) =>
          r.stateName.toLowerCase().includes(moverQuery) ||
          r.candidates.some((c) => c.name.toLowerCase().includes(moverQuery))
      )
    : activeRows;

  return (
    <div className="dashboard-background">
    <div className="mx-auto max-w-4xl px-4 pt-16 pb-8" style={{ color: "var(--text-secondary)"}}>
      <Link
        to="/"
        className="fixed top-4 left-4 z-20 inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm underline"
        style={{ color: "var(--text-muted)" }}
      >
        ← Back to home
      </Link>
      <header className="mb-8 text-center">
        {entries.length > 0 ? (
          <GooeyText
            texts={[title, partyFavoredLine, netSeatLine]}
            morphTime={1}
            cooldownTime={2.5}
            className="h-10 sm:h-12 md:h-14"
            textClassName="font-title px-2 text-2xl font-semibold sm:text-4xl md:text-5xl"
          />
        ) : (
          <h1 className="font-title text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
            {title}
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
            if (!entry || entry.candidates.length === 0) return null;

            const winner = [...entry.candidates].sort((a, b) => b.win_probability - a.win_probability)[0];
            if (!winner) return null;

            return {
              party: winner.party,
              winProbability: winner.win_probability,
              isFlip: winner.party !== entry.race.current_holder_party,
            };
          }}
          isClickable={(id) => id in racesByState}
          onStateClick={(id) => {
            const entry = racesByState[id];
            if (entry) navigate(`/states/${entry.race.slug}`);
          }}
          getTooltip={(id) => {
            const entry = racesByState[id];
            if (!entry || entry.candidates.length === 0) return null;

            // entry.candidates is already sorted by mean vote share, descending.
            const sorted = entry.candidates;
            const winner = sorted[0];

            return {
              candidates: sorted.map((r) => ({
                name: r.name,
                party: r.party,
                voteShare: r.mean_vote_share,
              })),
              winner: winner
                ? {
                    name: winner.name,
                    party: winner.party,
                    probability: winner.win_probability,
                  }
                : null,
            };
          }}
        />
      </section>

      <section className="glass-panel mt-6 rounded-lg p-5">
        <div className="relative mb-4 inline-block">
          <select
            value={viewMode}
            onChange={(e) => setViewMode(e.target.value as ViewMode)}
            className="title-select font-title cursor-pointer appearance-none py-1 pr-7 text-2xl font-semibold"
            style={{ color: "var(--text-primary)", backgroundColor: "transparent" }}
          >
            <option value="since-refresh">{SECTION_TITLES["since-refresh"]}</option>
            <option value="this-week">{SECTION_TITLES["this-week"]}</option>
            <option value="closest">{SECTION_TITLES["closest"]}</option>
          </select>
          <span
            className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 text-xl"
            style={{ color: "var(--text-muted)" }}
          >
            ▾
          </span>
        </div>
        {activeRows.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>{EMPTY_MESSAGES[viewMode]}</p>
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
            {filteredRows.length === 0 ? (
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
                        {viewMode === "closest" ? "Current split" : "Shift"}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row) => (
                      <tr
                        key={row.slug}
                        onClick={() => navigate(`/states/${row.slug}`)}
                        className="cursor-pointer border-b transition-opacity hover:opacity-70"
                        style={{ borderColor: "var(--border)" }}
                      >
                        <td
                          className="py-3 pr-4 pl-12 align-top font-medium"
                          style={{ color: "var(--text-primary)" }}
                        >
                          {row.stateName}
                        </td>
                        <td className="py-3 pr-4 pl-4 align-top">
                          <div className="flex flex-col gap-1.5">
                            {row.candidates.map((c) => (
                              <span key={c.name} style={{ color: "var(--text-secondary)" }}>
                                {c.name}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 pl-4 align-top">
                          <div className="flex flex-col gap-1.5">
                            {row.candidates.map((c) => (
                              <span
                                key={c.name}
                                className="font-semibold tabular-nums"
                                style={{ color: partyColorVar(c.party) }}
                              >
                                {viewMode === "closest"
                                  ? `${c.value.toFixed(1)}%`
                                  : `${partyAbbrev(c.party)} ${c.value >= 0 ? "▲" : "▼"} ${Math.abs(c.value).toFixed(1)} pts`}
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
