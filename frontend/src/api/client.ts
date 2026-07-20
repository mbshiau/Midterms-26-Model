import type {
  ForecastHistory,
  ForecastSnapshot,
  KalshiOdds,
  Poll,
  Race,
  RaceIntelligence,
  Simulations,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getRaces: () => request<Race[]>("/races"),
  getPolls: (slug: string) => request<Poll[]>(`/races/${slug}/polls`),
  getForecast: (slug: string) => request<ForecastSnapshot>(`/races/${slug}/forecast`),
  getForecastHistory: (slug: string) =>
    request<ForecastHistory>(`/races/${slug}/forecast/history`),
  getSimulations: (slug: string) => request<Simulations>(`/races/${slug}/simulations`),
  getKalshiOdds: (slug: string) => request<KalshiOdds[]>(`/races/${slug}/kalshi`),
  getRaceIntelligence: (slug: string) =>
    request<RaceIntelligence>(`/races/${slug}/intelligence`),
  simulate: (
    slug: string,
    params?: {
      n_simulations?: number;
      recency_half_life_days?: number;
      historical_error_stdev?: number;
    }
  ) =>
    request<ForecastSnapshot>(`/races/${slug}/simulate`, {
      method: "POST",
      body: JSON.stringify(params ?? {}),
    }),
};
