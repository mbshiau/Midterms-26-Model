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
    # Generic congressional ballot (see app.services.generic_ballot /
    # app.ingestion.generic_ballot_scraper): a second, more direct national-
    # environment signal blended alongside presidential approval (see
    # app.services.fundamentals.national_environment_adjustment).
    # generic_ballot_coefficient damps the raw national House-ballot margin
    # before it's blended in (a national House margin doesn't translate 1:1
    # into any one state's governor race); generic_ballot_weight is how much
    # of the final national-environment adjustment comes from the (damped)
    # ballot component vs. the approval-derived component.
    generic_ballot_coefficient: float = 0.5
    generic_ballot_weight: float = 0.5
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
    # Pollster quality (see app.services.pollster_ratings /
    # app.ingestion.pollster_ratings_scraper): a multiplier on top of the
    # existing recency x sample-size weighting, based on each pollster's
    # historical average error (in points) vs. certified results.
    # pollster_baseline_error_pts is the "typical" pollster's error --
    # quality_weight = baseline / avg_error, so a pollster right at the
    # baseline gets a neutral 1.0, a more accurate pollster gets upweighted,
    # a less accurate one downweighted. Clipped to
    # [pollster_quality_weight_floor, pollster_quality_weight_ceiling] so no
    # single pollster's rating (from a much smaller, less established source
    # than Wikipedia) can ever swamp or zero out a poll entirely.
    pollster_baseline_error_pts: float = 5.0
    pollster_quality_weight_floor: float = 0.5
    pollster_quality_weight_ceiling: float = 2.0
    # Correlated national polling-error component (see
    # app.services.simulation.generate_national_shock): real polling error is
    # highly correlated across states -- if polls miss for one party
    # nationally, they tend to miss the same way in most states at once, not
    # independently. Previously every race's Monte Carlo simulation drew
    # fully independent noise, which understates each individual race's own
    # uncertainty (not just cross-race correlation) by ignoring this
    # non-diversifiable risk. Applied as an additional shared shock to the
    # Democratic margin on top of (not a replacement for) each race's own
    # historical_error_stdev.
    national_error_stdev: float = 3.0

    # Kalshi prediction-market odds (see app.services.market_odds /
    # app.ingestion.kalshi_scraper): shown as its own standalone section per
    # race (app.routers.kalshi) -- never part of the forecasting model's
    # blend. RSA key pair from the user's own Kalshi account (Account
    # Settings -> API Keys). Every Kalshi endpoint requires a signed
    # request, including read-only market data -- unlike Wikipedia, which is
    # deliberately open to bots. Left blank by default so a dev environment
    # without Kalshi credentials just never resolves a ticker, rather than
    # needing a separate feature flag.
    kalshi_api_key_id: str = ""
    kalshi_private_key_path: str = ""
    kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"


settings = Settings()
