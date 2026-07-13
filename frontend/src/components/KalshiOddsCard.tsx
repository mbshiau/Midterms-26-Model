import { useState } from "react";
import type { KalshiOdds } from "../api/types";
import { partyColorVar } from "../lib/partyColor";

function Thumbnail({ odds }: { odds: KalshiOdds }) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const { photo_url, name } = odds.candidate;
  const color = partyColorVar(odds.candidate.party);

  if (photo_url && !photoFailed) {
    return (
      <img
        src={photo_url}
        alt={name}
        onError={() => setPhotoFailed(true)}
        className="h-8 w-8 flex-shrink-0 rounded-full object-cover"
        style={{ border: `2px solid ${color}` }}
      />
    );
  }
  return (
    <span
      className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
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

  return (
    <div>
      <div className="flex h-6 w-full gap-[2px]" role="img" aria-label="Kalshi win probability by candidate">
        {sorted.map((o) => (
          <div
            key={o.candidate.id}
            className="h-full first:rounded-l-[4px] last:rounded-r-[4px]"
            style={{
              width: `${Math.max(o.win_probability_pct, 0.5)}%`,
              backgroundColor: partyColorVar(o.candidate.party),
            }}
            title={`${o.candidate.name}: ${o.win_probability_pct.toFixed(1)}%`}
          />
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-3">
        {sorted.map((o) => (
          <div key={o.candidate.id} className="flex items-center gap-3">
            <Thumbnail odds={o} />
            <span className="flex-1 text-sm" style={{ color: "var(--text-secondary)" }}>
              {o.candidate.name}
            </span>
            <span className="text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
              {o.win_probability_pct.toFixed(1)}%
            </span>
            <a
              href={o.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs underline"
              style={{ color: "var(--text-muted)" }}
            >
              {o.ticker}
            </a>
          </div>
        ))}
      </div>

      <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
        Live prediction-market prices from Kalshi, refreshed twice daily. Shown for reference only
        -- not part of the forecast above. As of {new Date(mostRecent).toLocaleString()}.
      </p>
    </div>
  );
}
