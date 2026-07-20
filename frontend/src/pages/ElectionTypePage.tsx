import { Link } from "react-router-dom";

interface ElectionTypeOption {
  to: string;
  label: string;
  description: string;
}

const OPTIONS: ElectionTypeOption[] = [
  {
    to: "/governors",
    label: "Gubernatorial",
    description: "2026 governor races",
  },
  {
    to: "/senate",
    label: "Senate",
    description: "2026 U.S. Senate races",
  },
];

export function ElectionTypePage() {
  return (
    <div className="dashboard-background">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-4 py-16">
        <h1
          className="font-title mb-10 text-center text-3xl font-semibold sm:text-5xl"
          style={{ color: "var(--text-primary)" }}
        >
          2026 Election Forecast
        </h1>
        <div className="grid w-full grid-cols-1 gap-6 sm:grid-cols-2">
          {OPTIONS.map((option) => (
            <Link
              key={option.to}
              to={option.to}
              className="glass-panel flex flex-col items-center gap-2 rounded-lg p-10 text-center transition-opacity hover:opacity-80"
            >
              <span
                className="font-title text-2xl font-semibold sm:text-3xl"
                style={{ color: "var(--text-primary)" }}
              >
                {option.label}
              </span>
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                {option.description}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
