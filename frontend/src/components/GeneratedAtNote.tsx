/** Small "Updated <time>" footer for AI-generated text -- no inline "AI"
 * badge (see InfoButton for the one-time disclosure that Race Intelligence
 * text is AI-generated, instead of repeating a label on every card). */
export function GeneratedAtNote({ generatedAt }: { generatedAt: string | null }) {
  if (!generatedAt) return null;

  return (
    <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
      Updated{" "}
      {new Date(generatedAt).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })}
    </p>
  );
}
