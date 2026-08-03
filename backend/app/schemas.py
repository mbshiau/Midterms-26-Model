from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models import Population


def _as_utc_isoformat(value: datetime) -> str:
    """Postgres' plain DateTime column drops tzinfo on round-trip, even
    though every created_at value is written with datetime.now(timezone.utc).
    Without this, the API would emit a bare timestamp with no UTC marker,
    which browsers parse as local time instead of UTC -- silently shifting
    every displayed time by the viewer's UTC offset. Stamping it back on
    before serializing lets the frontend's `new Date(...)` (and
    toLocaleString) convert to the viewer's real local time correctly."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class RaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    state_code: str
    state_name: str
    office: str
    election_date: date
    current_holder_party: str | None


class RaceSummaryCandidateOut(BaseModel):
    name: str
    party: str
    mean_vote_share: float
    win_probability: float


class RaceSummaryDeltaOut(BaseModel):
    name: str
    party: str
    delta: float


class RaceSummaryOut(BaseModel):
    """Everything the map page's "movers"/"closest races" list and tooltip
    need for one race, in a single lightweight row -- see
    app.services.forecasting.race_movement_summary. Deliberately excludes
    the full forecast history and fundamentals_breakdown that /forecast and
    /forecast/history carry; fetch those per-race (state page) only when a
    single race's full detail is actually needed."""

    race: RaceOut
    latest_forecast_created_at: str | None
    candidates: list[RaceSummaryCandidateOut]
    since_refresh: list[RaceSummaryDeltaOut] | None
    this_week: list[RaceSummaryDeltaOut] | None


class SeatScenarioRaceOut(BaseModel):
    slug: str
    state_code: str
    state_name: str
    name: str
    party: str
    margin: float


class SeatDotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rep_seats: int
    independent_seats: int
    count: int
    probability: float
    example_race_winners: list[SeatScenarioRaceOut]


class SeatScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dem_seats: int
    count: int
    probability: float
    dominant_outcome: str
    dots: list[SeatDotOut]


class ChamberControlOut(BaseModel):
    """Powers the Senate control dot plot -- see
    app.services.chamber_control.simulate_chamber_control. Each entry in
    seat_distribution is one possible Democratic-seat total across the
    modeled races' Monte Carlo draws (bucketed); each entry's `dots` is one
    representative full-map scenario per ~100 draws in that bucket (see
    SIMULATIONS_PER_DOT), not a single example for the whole column --
    multiple different state-by-state combinations can land on the same
    total, so each dot is its own example, not the only path to that count."""

    model_config = ConfigDict(from_attributes=True)

    as_of: date
    n_simulations: int
    safe_dem_seats: int
    safe_rep_seats: int
    dem_win_probability: float
    rep_win_probability: float
    seat_distribution: list[SeatScenarioOut]


class ChamberControlHistoryPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of: date
    expected_dem_seats: float
    expected_rep_seats: float
    expected_independent_seats: float
    dem_win_probability: float
    rep_win_probability: float


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    party: str
    incumbent: bool
    photo_url: str | None = None
    kalshi_ticker: str | None = None


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
    # Governor/Senate-only fields (see app.services.fundamentals.
    # FundamentalsBreakdown) -- None for a House race, which has no
    # gubernatorial/Senate/presidential state-level lean of its own and
    # populates the district_* fields below instead (see
    # app.services.fundamentals.DistrictFundamentalsBreakdown).
    gubernatorial_lean_pts: float | None = None
    senate_lean_pts: float | None = None
    presidential_lean_pts: float | None = None
    combined_historical_lean_pts: float | None = None
    gubernatorial_elections_count: int | None = None
    senate_elections_count: int | None = None
    presidential_elections_count: int | None = None
    # House-only fields -- None for a Governor/Senate race.
    district_pvi_lean_pts: float | None = None
    district_house_lean_pts: float | None = None
    combined_district_lean_pts: float | None = None
    district_house_elections_count: int | None = None
    # Shared across every office.
    incumbency_pts: float
    # Governor/Senate only -- no per-district voter-registration dataset
    # exists, so a House race's breakdown simply doesn't produce this key.
    registration_trend_pts: float | None = None
    national_environment_pts: float
    total_dem_margin_pts: float
    president_name: str
    president_approval_pct: float
    president_approval_as_of: date
    president_approval_source_url: str
    # Optional: forecast snapshots generated before this feature existed have
    # no generic-ballot data in their stored JSON at all.
    generic_ballot_dem_pct: float | None = None
    generic_ballot_rep_pct: float | None = None
    generic_ballot_as_of: date | None = None
    generic_ballot_source_url: str | None = None


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

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return _as_utc_isoformat(value)


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

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return _as_utc_isoformat(value)


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


class NewsArticleOut(BaseModel):
    """One scraped headline for the race -- display-only context, not part
    of the forecasting model. ai_relevance is a per-article 1-2 sentence
    AI-generated blurb (see app.services.ai_summary.generate_article_relevance)
    -- None until that generation has run at least once for this article."""

    model_config = ConfigDict(from_attributes=True)

    headline: str
    source: str
    url: str
    published_at: datetime
    ai_relevance: str | None = None

    @field_serializer("published_at")
    def _serialize_published_at(self, value: datetime) -> str:
        return _as_utc_isoformat(value)


class RaceIntelligenceOut(BaseModel):
    """The Race Intelligence section's data: recent headlines (each with an
    AI relevance blurb) and an AI-generated model-vs-Kalshi comparison.
    Kalshi odds themselves are served by the existing /kalshi endpoint, not
    duplicated here."""

    news_articles: list[NewsArticleOut]
    market_analysis: str | None
    market_analysis_generated_at: datetime | None

    @field_serializer("market_analysis_generated_at")
    def _serialize_generated_at(self, value: datetime | None) -> str | None:
        return _as_utc_isoformat(value) if value is not None else None


class KalshiOddsOut(BaseModel):
    """A candidate's latest Kalshi market price -- a standalone prediction-
    market data point, not part of the forecasting model's blend."""

    model_config = ConfigDict(from_attributes=True)

    candidate: CandidateOut
    ticker: str
    win_probability_pct: float
    as_of: datetime
    source_url: str

    @field_serializer("as_of")
    def _serialize_as_of(self, value: datetime) -> str:
        return _as_utc_isoformat(value)
