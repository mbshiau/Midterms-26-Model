export interface Race {
  slug: string;
  state_code: string;
  state_name: string;
  office: string;
  election_date: string;
  // null means no real basis to name a holder (e.g. a scaffolded House
  // district, or a redrawn-map state where the old district's history
  // can't be attributed to the new lines) -- never treat this as a
  // flip-able party of its own; see current_holder_party in the backend.
  current_holder_party: string | null;
}

export interface Candidate {
  id: number;
  name: string;
  party: string;
  incumbent: boolean;
  photo_url: string | null;
  kalshi_ticker: string | null;
}

export interface PollResult {
  candidate: Candidate;
  pct: number;
}

export interface Poll {
  id: number;
  pollster: string;
  sponsor: string | null;
  field_start_date: string;
  field_end_date: string;
  release_date: string;
  sample_size: number;
  population: "LV" | "RV" | "A" | "V";
  margin_of_error: number | null;
  undecided_pct: number;
  source_url: string;
  results: PollResult[];
  weight: number;
}

export interface ForecastResult {
  candidate: Candidate;
  mean_vote_share: number;
  median_vote_share: number;
  std_dev: number;
  win_probability: number;
  ci_low: number;
  ci_high: number;
  polling_vote_share: number;
  fundamentals_vote_share: number;
}

export interface FundamentalsBreakdown {
  gubernatorial_lean_pts: number;
  senate_lean_pts: number;
  presidential_lean_pts: number;
  combined_historical_lean_pts: number;
  incumbency_pts: number;
  registration_trend_pts: number;
  national_environment_pts: number;
  total_dem_margin_pts: number;
  president_name: string;
  president_approval_pct: number;
  president_approval_as_of: string;
  president_approval_source_url: string;
  generic_ballot_dem_pct: number | null;
  generic_ballot_rep_pct: number | null;
  generic_ballot_as_of: string | null;
  generic_ballot_source_url: string | null;
  gubernatorial_elections_count: number;
  senate_elections_count: number;
  presidential_elections_count: number;
}

export interface ForecastSnapshot {
  id: number;
  created_at: string;
  method_version: string;
  n_simulations: number;
  n_polls_used: number;
  poll_weight_alpha: number;
  fundamentals_breakdown: FundamentalsBreakdown;
  results: ForecastResult[];
}

export interface SimulationHistogram {
  candidate: Candidate;
  bin_edges: number[];
  counts: number[];
  draws_sample: number[];
}

export interface Simulations {
  snapshot_id: number;
  created_at: string;
  n_simulations: number;
  histograms: SimulationHistogram[];
}

export interface ActualResult {
  candidate: Candidate;
  vote_pct: number;
  certified_date: string;
  source_url: string;
}

export interface ForecastHistory {
  snapshots: ForecastSnapshot[];
  actuals: ActualResult[];
  election_date: string;
}

export interface RaceSummaryCandidate {
  name: string;
  party: string;
  mean_vote_share: number;
  win_probability: number;
}

export interface RaceSummaryDelta {
  name: string;
  party: string;
  delta: number;
}

export interface RaceSummary {
  race: Race;
  latest_forecast_created_at: string | null;
  candidates: RaceSummaryCandidate[];
  since_refresh: RaceSummaryDelta[] | null;
  this_week: RaceSummaryDelta[] | null;
}

export interface SeatScenarioRace {
  slug: string;
  state_code: string;
  state_name: string;
  name: string;
  party: string;
  margin: number;
}

export interface SeatDot {
  rep_seats: number;
  independent_seats: number;
  count: number;
  probability: number;
  example_race_winners: SeatScenarioRace[];
}

export interface SeatScenario {
  dem_seats: number;
  count: number;
  probability: number;
  dominant_outcome: "Democratic" | "Republican";
  dots: SeatDot[];
}

export interface ChamberControlHistoryPoint {
  as_of: string;
  expected_dem_seats: number;
  expected_rep_seats: number;
  expected_independent_seats: number;
  dem_win_probability: number;
  rep_win_probability: number;
}

export interface ChamberControl {
  as_of: string;
  n_simulations: number;
  safe_dem_seats: number;
  safe_rep_seats: number;
  dem_win_probability: number;
  rep_win_probability: number;
  seat_distribution: SeatScenario[];
}

export interface KalshiOdds {
  candidate: Candidate;
  ticker: string;
  win_probability_pct: number;
  as_of: string;
  source_url: string;
}

export interface NewsArticle {
  headline: string;
  source: string;
  url: string;
  published_at: string;
  /** 1-2 sentence AI blurb: what the headline suggests + why it's relevant. Null until generated. */
  ai_relevance: string | null;
}

export interface RaceIntelligence {
  news_articles: NewsArticle[];
  market_analysis: string | null;
  market_analysis_generated_at: string | null;
}
