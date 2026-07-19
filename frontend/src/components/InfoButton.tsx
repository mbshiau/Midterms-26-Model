import { useEffect, useRef, useState } from "react";

/** Small "?" trigger that pops a panel out of the button explaining how the
 * forecast model works -- consolidates methodology notes (polls-vs-fundamentals
 * blending, historical lean weighting, Kalshi being display-only, the
 * fundamentals-only case) that used to be scattered across several cards/banners
 * on the page into one place. Deliberately not a centered modal with a
 * blocking backdrop: it anchors to the corner button and leaves the rest of
 * the page (including scrolling) untouched while open. */
export function InfoButton() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickAway = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickAway);
    return () => document.removeEventListener("mousedown", handleClickAway);
  }, [open]);

  return (
    <div ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label="How this forecast works"
        className="fixed bottom-6 right-6 z-40 inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border text-base font-semibold shadow-md"
        style={{ borderColor: "var(--border)", color: "var(--text-muted)", backgroundColor: "var(--surface)" }}
      >
        ?
      </button>

      <div
        className="fixed bottom-20 right-6 z-40 w-[min(24rem,calc(100vw-3rem))] origin-bottom-right rounded-lg p-5 text-left shadow-lg transition-all duration-150"
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          maxHeight: "70vh",
          overflowY: "auto",
          opacity: open ? 1 : 0,
          transform: open ? "scale(1)" : "scale(0.95)",
          pointerEvents: open ? "auto" : "none",
        }}
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          <h2 className="font-title text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
            How this forecast works
          </h2>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close"
            className="flex-shrink-0 text-xl leading-none"
            style={{ color: "var(--text-muted)" }}
          >
            ×
          </button>
        </div>

        <div className="flex flex-col gap-3 text-sm" style={{ color: "var(--text-secondary)" }}>
          <p>
            Each forecast blends two components: a <strong>live polling average</strong> and a{" "}
            <strong>fundamentals model</strong>. Early in the race, before much polling exists, the
            forecast leans almost entirely on fundamentals; the weight shifts toward polling as
            Election Day approaches and more data accumulates. If no general-election polling has
            been published yet for a race, that forecast is 100% fundamentals-only.
          </p>
          <p>
            The fundamentals model combines the state's historical partisan lean (a recency-weighted
            blend of the last several gubernatorial, Senate, and presidential races — weighted 45% /
            30% / 25% respectively) with incumbency, voter registration trends, and the national
            political environment (presidential approval blended with the generic congressional
            ballot).
          </p>
          <p>
            <strong>Kalshi prediction-market odds</strong>, shown separately on race pages that have a
            linked market, are for reference only — they are never blended into or used as an input to
            the forecast above them.
          </p>
          <p>
            The <strong>Race Intelligence</strong> section (news relevance notes and the market-vs-model
            comparison) is AI-generated from recent headlines and the data above — it's written by a
            language model, not an editor, and like Kalshi it's shown for context only and never feeds
            back into the forecast itself.
          </p>
        </div>
      </div>
    </div>
  );
}
