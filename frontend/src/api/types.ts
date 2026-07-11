export interface Race {
  state_code: string;
  state_name: string;
  office: string;
  election_date: string;
  current_holder_party: string;
}

export interface Candidate {
  id: number;
  name: string;
  party: string;
  incumbent: boolean;
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
  population: "LV" | "RV" | "A";
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
