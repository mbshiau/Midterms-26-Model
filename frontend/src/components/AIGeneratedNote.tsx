/** Small "AI-generated ... as of <time>" footer shared by the news-summary
 * and market-analysis cards -- keeps the disclaimer identical wherever
 * AI-written text is shown. */
export function AIGeneratedNote({ generatedAt }: { generatedAt: string | null }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
      <span
        className="rounded-full px-2 py-0.5 font-semibold tracking-wide"
        style={{ backgroundColor: "var(--gridline)", color: "var(--text-muted)" }}
      >
        AI-GENERATED
      </span>
      {generatedAt && (
        <span>
          as of{" "}
          {new Date(generatedAt).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </span>
      )}
    </div>
  );
}
