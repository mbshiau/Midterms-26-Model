from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import Population


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    party: str
    incumbent: bool


class PollResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate: CandidateOut
    pct: float


class PollOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pollster: str
    sponsor: str | None
    field_start_date: date
    field_end_date: date
    release_date: date
    sample_size: int
    population: Population
    margin_of_error: float | None
    undecided_pct: float
    source_url: str
    results: list[PollResultOut]
    weight: float = 0.0


class ForecastResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate: CandidateOut
    mean_vote_share: float
    median_vote_share: float
    std_dev: float
    win_probability: float
    ci_low: float
    ci_high: float
    polling_vote_share: float
    fundamentals_vote_share: float


class FundamentalsBreakdownOut(BaseModel):
    gubernatorial_lean_pts: float
    presidential_lean_pts: float
    combined_historical_lean_pts: float
    incumbency_pts: float
    registration_trend_pts: float
    national_environment_pts: float
    total_dem_margin_pts: float
    president_name: str
    president_approval_pct: float
    president_approval_as_of: date
    president_approval_source_url: str


class ForecastSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    method_version: str
    n_simulations: int
    n_polls_used: int
    poll_weight_alpha: float
    fundamentals_breakdown: FundamentalsBreakdownOut
    results: list[ForecastResultOut]


class SimulationHistogramOut(BaseModel):
    candidate: CandidateOut
    bin_edges: list[float]
    counts: list[int]
    draws_sample: list[float]


class SimulationsOut(BaseModel):
    snapshot_id: int
    created_at: datetime
    n_simulations: int
    histograms: list[SimulationHistogramOut]


class SimulateRequest(BaseModel):
    n_simulations: int | None = None
    recency_half_life_days: float | None = None
    historical_error_stdev: float | None = None


class ActualResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate: CandidateOut
    vote_pct: float
    certified_date: date
    source_url: str


class ForecastHistoryOut(BaseModel):
    snapshots: list[ForecastSnapshotOut]
    actuals: list[ActualResultOut]
    election_date: date
