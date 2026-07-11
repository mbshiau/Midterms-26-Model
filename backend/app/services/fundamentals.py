"""Fundamentals model: a polls-independent estimate of the race, blended
with the polling average in app.services.forecasting.generate_forecast.

Combines four inputs into a single projected Democratic-vs-Republican
two-party margin (positive favors the Democratic candidate). Every function
here takes the race's data as a parameter (from
app.data.fundamentals_data.RACE_FUNDAMENTALS[state_code]) rather than
reading a hardcoded constant, so the same model runs for any state:

1. Historical lean — a blend of three recency-weighted series, all genuinely
   statewide races: this state's gubernatorial results (weighted
   `gubernatorial_lean_weight`, since it's the same office), its Senate
   results (`senate_lean_weight`), and its presidential results (the
   remainder). Each series is independently recency-weighted by half-life
   decay so more recent elections count for more.
2. Incumbency — a fixed bonus for whichever party currently holds the seat
   and is running for reelection (0 for an open seat).
3. Registration trend — the recent trajectory of the statewide D-minus-R
   voter registration lead, damped into a small vote-share adjustment.
   States that don't register voters by party (e.g. Ohio) simply pass an
   empty list, which is a no-op (0 adjustment) rather than a fabricated one.
4. National environment — a thermostatic adjustment from the sitting
   president's approval rating: when it's below 50%, the president's party
   tends to underperform in other races, and vice versa. Approval/party are
   passed in rather than read from a constant, since they're refreshed daily
   by app.ingestion.approval_scraper and stored in the PresidentApproval
   table — this module stays a pure function of its inputs, easy to test.
"""

import math
from dataclasses import dataclass
from datetime import date

from app.config import settings
from app.data.fundamentals_data import ELECTION_DATE


@dataclass
class FundamentalsBreakdown:
    gubernatorial_lean_pts: float
    senate_lean_pts: float
    presidential_lean_pts: float
    combined_historical_lean_pts: float
    incumbency_pts: float
    registration_trend_pts: float
    national_environment_pts: float
    total_dem_margin_pts: float


def _recency_weighted_dem_margin(
    elections: list[dict], as_of: date, half_life_years: float
) -> float:
    """Recency-weighted average Democratic two-party margin across a series
    of past elections, decaying by half-life: an election `half_life_years`
    old counts for half as much as one from today."""
    weighted_sum = 0.0
    weight_total = 0.0
    for election in elections:
        years_ago = (as_of.year - election["year"]) + (as_of.month - 11) / 12
        weight = 0.5 ** (years_ago / half_life_years) if half_life_years > 0 else 1.0
        margin = 2 * election["dem_share"] - 100
        weighted_sum += margin * weight
        weight_total += weight

    return weighted_sum / weight_total if weight_total > 0 else 0.0


def gubernatorial_lean(gubernatorial_elections: list[dict], as_of: date | None = None) -> float:
    """Recency-weighted Democratic margin across a state's past governor races."""
    as_of = as_of or date.today()
    return _recency_weighted_dem_margin(
        gubernatorial_elections, as_of, settings.gubernatorial_election_half_life_years
    )


def senate_lean(senate_elections: list[dict], as_of: date | None = None) -> float:
    """Recency-weighted Democratic margin across a state's past Senate races."""
    as_of = as_of or date.today()
    return _recency_weighted_dem_margin(
        senate_elections, as_of, settings.senate_election_half_life_years
    )


def presidential_lean(presidential_elections: list[dict], as_of: date | None = None) -> float:
    """Recency-weighted Democratic margin across a state's past presidential races."""
    as_of = as_of or date.today()
    return _recency_weighted_dem_margin(
        presidential_elections, as_of, settings.presidential_election_half_life_years
    )


def _historical_lean_weights() -> tuple[float, float, float]:
    """(governor, senate, president) weights; president is the remainder so
    the three always sum to 1 regardless of how the first two are tuned."""
    w_gov = settings.gubernatorial_lean_weight
    w_sen = settings.senate_lean_weight
    return w_gov, w_sen, 1 - w_gov - w_sen


def combined_historical_lean(
    gubernatorial_elections: list[dict],
    senate_elections: list[dict],
    presidential_elections: list[dict],
    as_of: date | None = None,
) -> float:
    """Blends the governor/Senate/presidential leans by the weights above."""
    w_gov, w_sen, w_pres = _historical_lean_weights()
    return (
        w_gov * gubernatorial_lean(gubernatorial_elections, as_of)
        + w_sen * senate_lean(senate_elections, as_of)
        + w_pres * presidential_lean(presidential_elections, as_of)
    )


def incumbency_adjustment(incumbent_party: str | None) -> float:
    """Signed points added to the Democratic margin for the incumbent party."""
    if incumbent_party == "Democratic":
        return settings.incumbency_bonus_pts
    if incumbent_party == "Republican":
        return -settings.incumbency_bonus_pts
    return 0.0


def registration_trend_adjustment(registration_snapshots: list[dict]) -> float:
    """Small adjustment from the trailing trend in the D-R registration lead.

    Uses the two most recent snapshots' percent change in the lead, damped by
    a small coefficient so short-term registration swings can't dominate the
    forecast the way they might a naive read of the raw numbers. States with
    no party registration (an empty list) get a neutral 0.
    """
    if len(registration_snapshots) < 2:
        return 0.0

    prev, latest = registration_snapshots[-2], registration_snapshots[-1]
    if prev["dem_lead"] == 0:
        return 0.0

    pct_change = (latest["dem_lead"] - prev["dem_lead"]) / abs(prev["dem_lead"])
    return pct_change * 100 * settings.registration_trend_coefficient


def national_environment_adjustment(approval_pct: float, president_party: str) -> float:
    """Thermostatic adjustment: low presidential approval favors the out-party."""
    swing_toward_out_party = settings.presidential_approval_coefficient * (50 - approval_pct)
    if president_party == "Democratic":
        return -swing_toward_out_party
    return swing_toward_out_party


def fundamentals_breakdown(
    race_fundamentals: dict,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
) -> FundamentalsBreakdown:
    as_of = as_of or date.today()
    gub_elections = race_fundamentals["gubernatorial_elections"]
    sen_elections = race_fundamentals["senate_elections"]
    pres_elections = race_fundamentals["presidential_elections"]
    reg_snapshots = race_fundamentals["registration_snapshots"]

    gub = gubernatorial_lean(gub_elections, as_of)
    sen = senate_lean(sen_elections, as_of)
    pres = presidential_lean(pres_elections, as_of)
    w_gov, w_sen, w_pres = _historical_lean_weights()
    combined = w_gov * gub + w_sen * sen + w_pres * pres
    inc = incumbency_adjustment(incumbent_party)
    reg = registration_trend_adjustment(reg_snapshots)
    env = national_environment_adjustment(approval_pct, president_party)
    return FundamentalsBreakdown(
        gubernatorial_lean_pts=gub,
        senate_lean_pts=sen,
        presidential_lean_pts=pres,
        combined_historical_lean_pts=combined,
        incumbency_pts=inc,
        registration_trend_pts=reg,
        national_environment_pts=env,
        total_dem_margin_pts=combined + inc + reg + env,
    )


def fundamentals_vote_share(
    race_fundamentals: dict,
    party: str,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
) -> float:
    """Projected two-party vote share for a candidate of the given party."""
    margin = fundamentals_breakdown(
        race_fundamentals, incumbent_party, approval_pct, president_party, as_of
    ).total_dem_margin_pts
    if party == "Democratic":
        return 50 + margin / 2
    if party == "Republican":
        return 50 - margin / 2
    return 50.0


def poll_weight_for_election(election_date: date, as_of: date | None = None) -> float:
    """Fraction of weight given to polling (vs. fundamentals): a continuous
    exponential decay in days-to-election, approximating a hand-specified
    step schedule (~0.80 within 2 weeks, ~0.60 around 5 weeks out, ~0.40
    around 4 months out, asymptoting toward `poll_weight_floor` beyond that)
    without that schedule's discontinuous jumps."""
    as_of = as_of or date.today()
    days_to_election = max(0, (election_date - as_of).days)
    floor = settings.poll_weight_floor
    ceiling = settings.poll_weight_ceiling
    tau = settings.poll_weight_decay_tau_days
    return floor + (ceiling - floor) * math.exp(-days_to_election / tau)
