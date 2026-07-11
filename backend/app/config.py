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
    # separately since governor and presidential races run on different
    # cycles (4-year vs. 4-year, but offset).
    gubernatorial_election_half_life_years: float = 12.0
    presidential_election_half_life_years: float = 12.0
    # How much of the combined historical lean comes from governor races vs.
    # presidential races. Governor races are weighted higher since they're
    # more directly analogous to this race (same office, same electorate
    # behavior toward gubernatorial candidates specifically); presidential
    # races still add signal about the state's baseline partisanship.
    gubernatorial_lean_weight: float = 0.6
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
