import type { ForecastHistory, ForecastSnapshot, Poll, Simulations } from "./types";

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
  getPolls: () => request<Poll[]>("/polls"),
  getForecast: () => request<ForecastSnapshot>("/forecast"),
  getForecastHistory: () => request<ForecastHistory>("/forecast/history"),
  getSimulations: () => request<Simulations>("/simulations"),
  simulate: (params?: {
    n_simulations?: number;
    recency_half_life_days?: number;
    historical_error_stdev?: number;
  }) =>
    request<ForecastSnapshot>("/simulate", {
      method: "POST",
      body: JSON.stringify(params ?? {}),
    }),
};
