import { lazy, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ChamberControl, RaceSummary } from "../api/types";
import { Orb } from "../components/Orb";
import { UsMap, type StateVisual } from "../components/UsMap";
import { leadingCandidate } from "../lib/leadingCandidate";
import { partyColorVar } from "../lib/partyColor";

// Lazy-loaded: the House district shape data is ~900KB on its own and was
// otherwise bundled into every page's initial JS (see vite build's chunk-size
// warning) even though /senate, /governors, and state-detail pages never
// render it -- splitting it into its own chunk, fetched only when this
// mini-map card (or the full /house map) actually renders, shrinks every
// other route's initial bundle substantially.
const HouseDistrictMap = lazy(() =>
  import("../components/HouseDistrictMap").then((m) => ({ default: m.HouseDistrictMap }))
);

interface RaceGroup {
  entries: RaceSummary[];
  demCount: number;
  repCount: number;
  lastUpdated: number;
}

function loadGroup(office: "Governor" | "Senate" | "House"): Promise<RaceGroup> {
  return api.getRaceSummaries(office).then((entries) => ({
    entries,
    demCount: entries.filter((r) => leadingCandidate(r.candidates)?.party === "Democratic").length,
    repCount: entries.filter((r) => leadingCandidate(r.candidates)?.party === "Republican").length,
    lastUpdated: entries
      .map((r) => r.latest_forecast_created_at)
      .filter((ts): ts is string => Boolean(ts))
      .map((ts) => new Date(ts).getTime())
      .reduce((max, ts) => Math.max(max, ts), 0),
  }));
}

function visualFor(entries: RaceSummary[]): (stateId: string) => StateVisual | null {
  const byState = Object.fromEntries(entries.map((r) => [r.race.state_code.toLowerCase(), r]));
  return (stateId) => {
    const entry = byState[stateId];
    const winner = entry && leadingCandidate(entry.candidates);
    if (!entry || !winner) return null;
    return {
      party: winner.party,
      winProbability: winner.win_probability,
      isFlip: winner.party !== entry.race.current_holder_party,
    };
  };
}

function houseVisualsFor(entries: RaceSummary[]) {
  return Object.fromEntries(
    entries
      .map((r) => ({ r, winner: leadingCandidate(r.candidates) }))
      .filter((x): x is { r: RaceSummary; winner: NonNullable<typeof x.winner> } => Boolean(x.winner))
      .map(({ r, winner }) => [
        r.race.slug,
        {
          party: winner.party,
          winProbability: winner.win_probability,
          isFlip: winner.party !== r.race.current_holder_party,
        },
      ])
  );
}

function MiniMapCard({
  to,
  label,
  headline,
  map,
}: {
  to: string;
  label: string;
  headline: React.ReactNode;
  map: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className="glass-panel flex flex-col gap-3 rounded-2xl p-5 text-center transition-transform hover:-translate-y-1"
    >
      <div className="px-6" style={{ pointerEvents: "none" }}>
        {map}
      </div>
      <span className="font-title text-xs font-semibold tracking-wide" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
      <span className="text-lg" style={{ color: "var(--text-primary)" }}>
        {headline}
      </span>
    </Link>
  );
}

const NAV_LINKS = [
  { to: "/", label: "Home", icon: HomeIcon, exact: true },
  { to: "/senate", label: "Senate", icon: LandmarkIcon, exact: false },
  { to: "/governors", label: "Gubernatorial", icon: ShieldIcon, exact: false },
  { to: "/house", label: "House", icon: CapitolIcon, exact: false },
];

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9.5a1 1 0 0 0 1 1H10v-6h4v6h3.5a1 1 0 0 0 1-1V10" />
    </svg>
  );
}

function LandmarkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M4 21h16" />
      <path d="M5 10.5v9" />
      <path d="M9.5 10.5v9" />
      <path d="M14.5 10.5v9" />
      <path d="M19 10.5v9" />
      <path d="M3.5 10.5 12 4l8.5 6.5" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M12 3.5 19 6.5v5.5c0 4.7-3 7.6-7 8.5-4-.9-7-3.8-7-8.5V6.5Z" />
    </svg>
  );
}

function CapitolIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
      <path d="M4 21h16" />
      <path d="M5 21V11" />
      <path d="M19 21V11" />
      <path d="M12 3 3.5 9h17L12 3Z" />
      <path d="M8 11v7" />
      <path d="M12 11v7" />
      <path d="M16 11v7" />
    </svg>
  );
}

export function ElectionTypePage() {
  const [senate, setSenate] = useState<RaceGroup | null>(null);
  const [governor, setGovernor] = useState<RaceGroup | null>(null);
  const [house, setHouse] = useState<RaceGroup | null>(null);
  const [chamberControl, setChamberControl] = useState<ChamberControl | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadGroup("Senate"), loadGroup("Governor"), loadGroup("House"), api.getSenateControl()]).then(
      ([senateGroup, governorGroup, houseGroup, control]) => {
        if (cancelled) return;
        setSenate(senateGroup);
        setGovernor(governorGroup);
        setHouse(houseGroup);
        setChamberControl(control);
      }
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const loaded = senate && governor && house && chamberControl;
  const lastUpdated = Math.max(senate?.lastUpdated ?? 0, governor?.lastUpdated ?? 0, house?.lastUpdated ?? 0);

  const demPct = chamberControl ? chamberControl.dem_win_probability : 0;
  const repPct = chamberControl ? chamberControl.rep_win_probability : 0;
  const leadingParty = demPct >= repPct ? "Democratic" : "Republican";
  const leadingPct = Math.max(demPct, repPct);
  const trailingParty = leadingParty === "Democratic" ? "Republican" : "Democratic";
  const trailingPct = Math.min(demPct, repPct);

  return (
    <div className="dashboard-background">
      <div className="mx-auto flex min-h-screen max-w-4xl flex-col items-center px-4 pt-16 pb-32">
        <h1
          className="font-title mb-2 text-center text-3xl font-semibold sm:text-5xl"
          style={{ color: "var(--text-primary)" }}
        >
          2026 Election Forecast
        </h1>
        {lastUpdated > 0 && (
          <p className="mb-10 text-sm" style={{ color: "var(--text-muted)" }}>
            Last updated {new Date(lastUpdated).toLocaleString()}
          </p>
        )}

        {!loaded ? (
          <p className="py-24" style={{ color: "var(--text-muted)" }}>
            Loading forecast…
          </p>
        ) : (
          <>
            <div className="mb-14 flex flex-wrap items-center justify-center gap-x-10 gap-y-8">
              <Orb value={`${(trailingPct * 100).toFixed(0)}%`} color={partyColorVar(trailingParty)} size="sm" floatDelay={0.4}>
                <span style={{ color: partyColorVar(trailingParty), fontWeight: 600 }}>{trailingParty}s</span>
                <br />
                path to Senate control
              </Orb>
              <Orb value={`${(leadingPct * 100).toFixed(0)}%`} color={partyColorVar(leadingParty)} size="lg" floatDelay={0}>
                <span style={{ color: partyColorVar(leadingParty), fontWeight: 600 }}>{leadingParty}s</span>{" "}
                favored to win Senate control
              </Orb>
              <Orb value={`${governor.demCount}`} color={partyColorVar("Democratic")} size="sm" floatDelay={0.8}>
                <span style={{ color: partyColorVar("Democratic"), fontWeight: 600 }}>Democrats</span> favored, of{" "}
                {governor.entries.length} governor races
              </Orb>
            </div>

            <div className="grid w-full grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <MiniMapCard
                to="/senate"
                label="SENATE"
                map={<UsMap getVisual={visualFor(senate.entries)} isClickable={() => false} onStateClick={() => {}} />}
                headline={
                  <>
                    <span style={{ color: partyColorVar(leadingParty), fontWeight: 600 }}>
                      {(leadingPct * 100).toFixed(0)}% chance
                    </span>{" "}
                    {leadingParty}s will control.
                  </>
                }
              />
              <MiniMapCard
                to="/governors"
                label="GUBERNATORIAL"
                map={<UsMap getVisual={visualFor(governor.entries)} isClickable={() => false} onStateClick={() => {}} />}
                headline={
                  <>
                    <span style={{ color: partyColorVar("Democratic"), fontWeight: 600 }}>Democrats</span> favored in{" "}
                    {governor.demCount} governor races.
                  </>
                }
              />
              <MiniMapCard
                to="/house"
                label="HOUSE"
                map={
                  <Suspense fallback={<div style={{ aspectRatio: "3 / 2" }} />}>
                    <HouseDistrictMap
                      districts={house.entries.map((e) => ({ slug: e.race.slug, stateCode: e.race.state_code }))}
                      visualsBySlug={houseVisualsFor(house.entries)}
                      onDistrictClick={() => {}}
                    />
                  </Suspense>
                }
                headline={
                  <>
                    <span style={{ color: partyColorVar("Democratic"), fontWeight: 600 }}>Democrats</span> favored in{" "}
                    {house.demCount} of {house.entries.length} House districts.
                  </>
                }
              />
            </div>
          </>
        )}
      </div>

      <nav className="glass-panel fixed bottom-6 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full px-2 py-2">
        {NAV_LINKS.map(({ to, label, icon: Icon, exact }) => (
          <Link
            key={to}
            to={to}
            className={`home-nav-link flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-medium ${exact ? "active" : ""}`}
          >
            <Icon />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
