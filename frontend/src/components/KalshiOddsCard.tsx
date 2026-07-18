import type { KalshiOdds } from "../api/types";
import { partyAbbrev, partyColorVar } from "../lib/partyColor";

function HeroPanel({ odds, borderSide }: { odds: KalshiOdds; borderSide: "left" | "right" }) {
  const color = partyColorVar(odds.candidate.party);
  const cents = Math.round(odds.win_probability_pct);

  return (
    <div
      className={`flex-1 p-5 ${borderSide === "left" ? "sm:border-r" : ""}`}
      style={{ borderColor: "var(--border)" }}
    >
      <div className="text-xs font-semibold tracking-wide" style={{ color: "var(--text-muted)" }}>
        {partyAbbrev(odds.candidate.party)} WIN
      </div>
      <div className="text-sm font-medium" style={{ color }}>
        {odds.candidate.name}
      </div>
      <div className="font-title text-6xl font-bold leading-none tabular-nums" style={{ color }}>
        {cents}¢
      </div>
      <a
        href={odds.source_url}
        target="_blank"
        rel="noreferrer"
        className="mt-2 inline-block text-xs underline"
        style={{ color: "var(--text-muted)" }}
      >
        {odds.ticker}
      </a>
    </div>
  );
}

export function KalshiOddsCard({ odds }: { odds: KalshiOdds[] }) {
  if (odds.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)" }}>
        No Kalshi prediction market has been linked for this race yet.
      </p>
    );
  }

  const sorted = [...odds].sort((a, b) => b.win_probability_pct - a.win_probability_pct);
  const mostRecent = sorted.reduce((latest, o) => (o.as_of > latest ? o.as_of : latest), sorted[0].as_of);
  const isTwoWay = sorted.length === 2;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div className="flex items-baseline gap-3">
          <h3
            className="font-title text-3xl font-bold"
            style={{
              backgroundImage: `linear-gradient(90deg, ${partyColorVar("Democratic")}, ${partyColorVar("Republican")})`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            Markets
          </h3>
          <span className="text-xs font-semibold tracking-wide" style={{ color: "var(--text-muted)" }}>
            KALSHI PREDICTION MARKET
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "#22c55e" }} />
          LIVE · {new Date(mostRecent).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
        </div>
      </div>

      <div
        className="overflow-hidden rounded-lg border"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--page)" }}
      >
        <div className={`flex flex-col ${isTwoWay ? "sm:flex-row" : ""}`}>
          {isTwoWay ? (
            sorted.map((o, i) => (
              <HeroPanel key={o.candidate.id} odds={o} borderSide={i === 0 ? "left" : "right"} />
            ))
          ) : (
            <div className="flex flex-wrap gap-4 p-5">
              {sorted.map((o) => (
                <div key={o.candidate.id} className="flex-1 min-w-[140px]">
                  <div className="text-xs font-semibold tracking-wide" style={{ color: "var(--text-muted)" }}>
                    {partyAbbrev(o.candidate.party)} WIN
                  </div>
                  <div className="text-sm font-medium" style={{ color: partyColorVar(o.candidate.party) }}>
                    {o.candidate.name}
                  </div>
                  <div
                    className="font-title text-4xl font-bold tabular-nums"
                    style={{ color: partyColorVar(o.candidate.party) }}
                  >
                    {Math.round(o.win_probability_pct)}¢
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex h-2 w-full" style={{ borderTop: "1px solid var(--border)" }}>
          {sorted.map((o) => (
            <div
              key={o.candidate.id}
              className="h-full"
              style={{
                width: `${Math.max(o.win_probability_pct, 0.5)}%`,
                backgroundColor: partyColorVar(o.candidate.party),
              }}
              title={`${o.candidate.name}: ${o.win_probability_pct.toFixed(1)}%`}
            />
          ))}
        </div>

        <div className="flex items-center justify-between px-5 py-2 text-xs font-medium">
          <span style={{ color: partyColorVar(sorted[0].candidate.party) }}>{sorted[0].candidate.name}</span>
          <span style={{ color: partyColorVar(sorted[sorted.length - 1].candidate.party) }}>
            {sorted[sorted.length - 1].candidate.name}
          </span>
        </div>
      </div>
    </div>
  );
}
