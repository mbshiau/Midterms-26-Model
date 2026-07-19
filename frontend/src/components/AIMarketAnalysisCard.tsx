import { GeneratedAtNote } from "./GeneratedAtNote";

export function AIMarketAnalysisCard({
  analysis,
  generatedAt,
}: {
  analysis: string | null;
  generatedAt: string | null;
}) {
  if (!analysis) {
    return (
      <p style={{ color: "var(--text-muted)" }}>
        Comparison will appear once a Kalshi market is linked for this race.
      </p>
    );
  }

  return (
    <div>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
        {analysis}
      </p>
      <GeneratedAtNote generatedAt={generatedAt} />
    </div>
  );
}
