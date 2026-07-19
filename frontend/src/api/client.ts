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
  getPolls: (stateCode: string) => request<Poll[]>(`/races/${stateCode}/polls`),
  getForecast: (stateCode: string) => request<ForecastSnapshot>(`/races/${stateCode}/forecast`),
  getForecastHistory: (stateCode: string) =>
    request<ForecastHistory>(`/races/${stateCode}/forecast/history`),
  getSimulations: (stateCode: string) => request<Simulations>(`/races/${stateCode}/simulations`),
  getKalshiOdds: (stateCode: string) => request<KalshiOdds[]>(`/races/${stateCode}/kalshi`),
  getRaceIntelligence: (stateCode: string) =>
    request<RaceIntelligence>(`/races/${stateCode}/intelligence`),
  simulate: (
    stateCode: string,
    params?: {
      n_simulations?: number;
      recency_half_life_days?: number;
      historical_error_stdev?: number;
    }
  ) =>
    request<ForecastSnapshot>(`/races/${stateCode}/simulate`, {
      method: "POST",
      body: JSON.stringify(params ?? {}),
    }),
};
