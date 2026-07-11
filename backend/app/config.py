from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://forecast:forecast@localhost:5432/pa_gov_forecast"
    recency_half_life_days: float = 21.0
    historical_error_stdev: float = 4.0
    default_n_simulations: int = 10_000
    cors_origins: str = "http://localhost:5173"

    # Fundamentals model (see app.services.fundamentals)
    # Half-life decay for recency-weighting past elections: an election this
    # many years old carries half the weight of one from today. Applied
    # separately since governor/Senate/presidential races run on different
    # (staggered) cycles.
    gubernatorial_election_half_life_years: float = 12.0
    senate_election_half_life_years: float = 12.0
    presidential_election_half_life_years: float = 12.0
    # How the combined historical lean splits across the three statewide
    # race types. Governor is weighted highest (same office); Senate next
    # (also genuinely statewide, and on a similar coalition to governor);
    # president gets the remainder — still useful baseline-partisanship
    # signal, but the most removed from a governor's race specifically.
    # Must sum to 1 (presidential weight is computed as the remainder).
    gubernatorial_lean_weight: float = 0.45
    senate_lean_weight: float = 0.30
    incumbency_bonus_pts: float = 4.0
    presidential_approval_coefficient: float = 0.15
    registration_trend_coefficient: float = 0.03
    fundamentals_uncertainty_stdev: float = 6.0
    # Poll weight follows a continuous exponential decay in days-to-election
    # (T): weight = floor + (ceiling - floor) * exp(-T / tau). Chosen to
    # approximate a discrete schedule (~0.80 within 2 weeks, ~0.60 around
    # 5 weeks out, ~0.40 around 4 months out, asymptoting toward the floor
    # beyond that) without the schedule's discontinuous jumps, which would
    # otherwise show up as artificial cliffs in the forecast-history chart.
    # The 0.80 ceiling (not 1.0) is deliberate: even on election day, some
    # weight stays on the structural prior as a hedge against correlated
    # late-poll error.
    poll_weight_floor: float = 0.25
    poll_weight_ceiling: float = 0.80
    poll_weight_decay_tau_days: float = 90.0


settings = Settings()
