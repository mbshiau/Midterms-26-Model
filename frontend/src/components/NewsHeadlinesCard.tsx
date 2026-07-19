import type { NewsArticle } from "../api/types";

function formatPublished(iso: string): string {
  const date = new Date(iso);
  const diffHours = (Date.now() - date.getTime()) / (1000 * 60 * 60);
  if (diffHours < 1) return "just now";
  if (diffHours < 24) return `${Math.round(diffHours)}h ago`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function NewsHeadlinesCard({ articles }: { articles: NewsArticle[] }) {
  if (articles.length === 0) {
    return <p style={{ color: "var(--text-muted)" }}>No recent coverage found yet.</p>;
  }

  const sorted = [...articles].sort(
    (a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
  );

  return (
    <ul className="flex flex-col">
      {sorted.map((article, i) => (
        <li
          key={article.url}
          className={`py-2.5 ${i > 0 ? "border-t" : "pt-0"} last:pb-0`}
          style={i > 0 ? { borderColor: "var(--border)" } : undefined}
        >
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium hover:underline"
            style={{ color: "var(--text-primary)" }}
          >
            {article.headline}
          </a>
          <div className="mt-1 flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>{article.source}</span>
            <span aria-hidden="true">·</span>
            <span>{formatPublished(article.published_at)}</span>
          </div>
          {article.ai_relevance && (
            <p className="mt-1.5 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              <span
                className="mr-1.5 inline-block rounded px-1 py-0.5 align-middle text-[10px] font-semibold tracking-wide"
                style={{ backgroundColor: "var(--gridline)", color: "var(--text-muted)" }}
              >
                AI
              </span>
              {article.ai_relevance}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
