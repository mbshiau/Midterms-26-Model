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
   decay so more recent elections count for more. A state can override the
   gov/Senate/president split, and how much the *combined* historical lean
   counts against the other three inputs, via an optional "model_overrides"
   dict on its RACE_FUNDAMENTALS entry -- see fundamentals_breakdown.
2. Incumbency — a fixed bonus for whichever party currently holds the seat
   and is running for reelection (0 for an open seat).
3. Registration trend — the recent trajectory of the statewide D-minus-R
   voter registration lead, damped into a small vote-share adjustment.
   States that don't register voters by party (e.g. Ohio) simply pass an
   empty list, which is a no-op (0 adjustment) rather than a fabricated one.
4. National environment — a thermostatic adjustment from the sitting
   president's approval rating: when it's below 50%, the president's party
   tends to underperform in other races, and vice versa. Optionally blended
   with a second, more direct signal -- the generic congressional ballot
   margin (Democratic minus Republican share, "if the election were held
   today") -- when one is available. Approval/party/ballot margin are all
   passed in rather than read from a constant, since they're refreshed daily
   by app.ingestion.approval_scraper / app.ingestion.generic_ballot_scraper
   and stored in the PresidentApproval / GenericBallot tables — this module
   stays a pure function of its inputs, easy to test.
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


@dataclass
class DistrictFundamentalsBreakdown:
    """The House counterpart to FundamentalsBreakdown -- kept as a separate
    dataclass rather than reusing the statewide one, since a single
    congressional district has no gubernatorial/Senate race of its own and
    repurposing those field names for district data would surface
    mislabeled numbers in the UI's "model composition" breakdown. See
    district_fundamentals_breakdown."""

    district_pvi_lean_pts: float
    district_house_lean_pts: float
    combined_district_lean_pts: float
    incumbency_pts: float
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


def _resolve_overrides(model_overrides: dict, office: str) -> dict:
    """Resolves a RACE_FUNDAMENTALS entry's "model_overrides" for the given
    office. A state with only one race (the common case, e.g. Vermont) just
    uses flat top-level keys, applied regardless of office. A state with
    *two* races that need genuinely different overrides (e.g. Ohio's
    Senate race excluding gubernatorial history entirely, while its
    Governor race's own weighting stays untouched) nests an office-keyed
    dict instead -- `{"Senate": {"gubernatorial_lean_weight": 0.0}}` --
    which is merged over the flat keys (and wins on conflict) only when
    resolving for that specific office."""
    office_specific = model_overrides.get(office)
    if isinstance(office_specific, dict):
        return {**model_overrides, **office_specific}
    return model_overrides


def _historical_lean_weights(
    model_overrides: dict | None = None, office: str = "Governor"
) -> tuple[float, float, float]:
    """(governor, senate, president) weights; president is the remainder so
    the three always sum to 1 regardless of how the first two are tuned.

    For a Governor race, the two global defaults
    (`settings.gubernatorial_lean_weight` / `settings.senate_lean_weight`)
    apply as written -- the same-office race is the stronger signal. For a
    **Senate** race, gubernatorial history is excluded entirely by default
    (weight 0) rather than merely de-emphasized: a state's governor race is
    often decided by dynamics (a popular incumbent, a scandal, an unusually
    strong/weak nominee) that don't reliably transfer to a Senate matchup,
    so it's dropped from the blend by default and its weight simply falls
    to president (the remainder) -- Senate history keeps the same weight it
    would have gotten from the old gov/Senate swap
    (`settings.gubernatorial_lean_weight`, still the stronger of the two
    non-president inputs). `model_overrides` (already resolved for `office`
    by `_resolve_overrides` -- see fundamentals_breakdown) can still
    override either weight for one specific state/office -- e.g. Phil
    Scott's Vermont, where the governor's own race is a far stronger signal
    than the state's Senate/presidential results, uses gov=0.70/sen=0.15;
    or a future Senate race where gubernatorial history genuinely should
    count, via `{"Senate": {"gubernatorial_lean_weight": <value>}}`."""
    model_overrides = model_overrides or {}
    if office == "Senate":
        default_gov, default_sen = 0.0, settings.gubernatorial_lean_weight
    else:
        default_gov, default_sen = settings.gubernatorial_lean_weight, settings.senate_lean_weight
    w_gov = model_overrides.get("gubernatorial_lean_weight", default_gov)
    w_sen = model_overrides.get("senate_lean_weight", default_sen)
    return w_gov, w_sen, 1 - w_gov - w_sen


def combined_historical_lean(
    gubernatorial_elections: list[dict],
    senate_elections: list[dict],
    presidential_elections: list[dict],
    as_of: date | None = None,
    model_overrides: dict | None = None,
    office: str = "Governor",
) -> float:
    """Blends the governor/Senate/presidential leans by the weights above."""
    resolved_overrides = _resolve_overrides(model_overrides or {}, office)
    w_gov, w_sen, w_pres = _historical_lean_weights(resolved_overrides, office)
    return (
        w_gov * gubernatorial_lean(gubernatorial_elections, as_of)
        + w_sen * senate_lean(senate_elections, as_of)
        + w_pres * presidential_lean(presidential_elections, as_of)
    )


def incumbency_adjustment(incumbent_party: str | None, office: str = "Governor") -> float:
    """Signed points added to the Democratic margin for the incumbent party.
    `office` picks the bonus magnitude -- House incumbency advantage is
    modeled separately (and smaller by default) than Governor/Senate's, see
    settings.house_incumbency_bonus_pts."""
    bonus = settings.house_incumbency_bonus_pts if office == "House" else settings.incumbency_bonus_pts
    if incumbent_party == "Democratic":
        return bonus
    if incumbent_party == "Republican":
        return -bonus
    return 0.0


def district_lean(
    pvi_dem_margin: float,
    house_elections: list[dict],
    as_of: date | None = None,
    weight: float | None = None,
) -> float:
    """Democratic margin for a single House district, blending (a) the
    district's Cook Partisan Voting Index -- already a two-cycle
    presidential-performance-vs-national-average figure computed on the
    district's *current* lines, so no separate recency-weighting is needed
    the way a raw multi-year election series gets -- with (b) the
    district's own prior House election results (recency-weighted the same
    way statewide races are, via _recency_weighted_dem_margin).

    `pvi_dem_margin` is a signed point value (positive favors the
    Democratic candidate) -- see DISTRICT_FUNDAMENTALS[key]["pvi_dem_margin_pts"],
    parsed from Cook PVI's own "D+N"/"R+N"/"EVEN" notation.

    `weight` (share on the PVI figure) defaults to settings.district_pvi_weight;
    a district can override it via
    DISTRICT_FUNDAMENTALS[key]["model_overrides"]["district_pvi_weight"],
    same convention as gubernatorial_lean_weight above.
    """
    as_of = as_of or date.today()
    weight = weight if weight is not None else settings.district_pvi_weight
    house = _recency_weighted_dem_margin(
        house_elections, as_of, settings.presidential_election_half_life_years
    )
    return weight * pvi_dem_margin + (1 - weight) * house


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


def national_environment_adjustment(
    approval_pct: float,
    president_party: str,
    generic_ballot_margin: float | None = None,
) -> float:
    """Thermostatic adjustment: low presidential approval favors the
    out-party. When a generic-congressional-ballot margin (Democratic minus
    Republican share) is also available, it's blended in alongside the
    approval-derived swing (weighted `generic_ballot_weight`) rather than
    relying on approval alone -- the ballot margin is a more direct read on
    "which way is the country leaning right now" but noisier and less
    predictive of any one specific governor's race than the resulting blend.
    Backward compatible: omitting generic_ballot_margin (the default) falls
    back to approval-only, exactly as before this was added.
    """
    swing_toward_out_party = settings.presidential_approval_coefficient * (50 - approval_pct)
    approval_component = -swing_toward_out_party if president_party == "Democratic" else swing_toward_out_party

    if generic_ballot_margin is None:
        return approval_component

    # A raw national House-ballot margin doesn't translate 1:1 into a single
    # state's governor race -- damped by generic_ballot_coefficient before
    # being blended in, the same way registration swings are damped.
    ballot_component = generic_ballot_margin * settings.generic_ballot_coefficient
    weight = settings.generic_ballot_weight
    return weight * ballot_component + (1 - weight) * approval_component


def fundamentals_breakdown(
    race_fundamentals: dict,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
    generic_ballot_margin: float | None = None,
    office: str = "Governor",
) -> FundamentalsBreakdown:
    """`office` ("Governor" or "Senate") determines which of the two
    historical-lean weights below is treated as the same-office (dominant)
    one -- see _historical_lean_weights. `race_fundamentals` may carry an
    optional "model_overrides" dict for states whose normal historical-lean
    assumptions don't fit well:

    - `gubernatorial_lean_weight` / `senate_lean_weight`: replace the two
      global defaults for this state's gov/Senate/president split (see
      _historical_lean_weights).
    - `historical_lean_share`: when present, switches from the default
      (historical lean + incumbency + registration + national environment,
      simply summed) to a weighted blend instead --
      `historical_lean_share * combined_historical_lean +
      (1 - historical_lean_share) * (incumbency + registration + national
      environment)` -- for a state where a specific candidate's own brand
      reliably overrides what the state's past elections would suggest
      (e.g. Iowa's Democratic nominee), so historical lean shouldn't simply
      dominate the total the way unweighted addition lets it.

    Either key can also be nested under an office name (e.g.
    `{"Senate": {"gubernatorial_lean_weight": 0.0}}`) for a state whose two
    races need different overrides -- see _resolve_overrides.
    """
    as_of = as_of or date.today()
    model_overrides = _resolve_overrides(race_fundamentals.get("model_overrides", {}), office)
    gub_elections = race_fundamentals["gubernatorial_elections"]
    sen_elections = race_fundamentals["senate_elections"]
    pres_elections = race_fundamentals["presidential_elections"]
    reg_snapshots = race_fundamentals["registration_snapshots"]

    gub = gubernatorial_lean(gub_elections, as_of)
    sen = senate_lean(sen_elections, as_of)
    pres = presidential_lean(pres_elections, as_of)
    w_gov, w_sen, w_pres = _historical_lean_weights(model_overrides, office)
    combined = w_gov * gub + w_sen * sen + w_pres * pres
    inc = incumbency_adjustment(incumbent_party)
    reg = registration_trend_adjustment(reg_snapshots)
    env = national_environment_adjustment(approval_pct, president_party, generic_ballot_margin)

    historical_lean_share = model_overrides.get("historical_lean_share")
    if historical_lean_share is None:
        total = combined + inc + reg + env
    else:
        total = historical_lean_share * combined + (1 - historical_lean_share) * (inc + reg + env)

    return FundamentalsBreakdown(
        gubernatorial_lean_pts=gub,
        senate_lean_pts=sen,
        presidential_lean_pts=pres,
        combined_historical_lean_pts=combined,
        incumbency_pts=inc,
        registration_trend_pts=reg,
        national_environment_pts=env,
        total_dem_margin_pts=total,
    )


def fundamentals_vote_share(
    race_fundamentals: dict,
    party: str,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
    generic_ballot_margin: float | None = None,
    office: str = "Governor",
) -> float:
    """Projected two-party vote share for a candidate of the given party."""
    margin = fundamentals_breakdown(
        race_fundamentals, incumbent_party, approval_pct, president_party, as_of, generic_ballot_margin, office
    ).total_dem_margin_pts
    if party == "Democratic":
        return 50 + margin / 2
    if party == "Republican":
        return 50 - margin / 2
    return 50.0


def district_fundamentals_breakdown(
    district_fundamentals: dict,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
    generic_ballot_margin: float | None = None,
) -> DistrictFundamentalsBreakdown:
    """The House counterpart to fundamentals_breakdown -- see
    DistrictFundamentalsBreakdown for why this is a separate function
    rather than an office branch inside fundamentals_breakdown.
    `district_fundamentals` is one app.data.district_fundamentals_data.
    DISTRICT_FUNDAMENTALS entry (pvi_dem_margin_pts, house_elections,
    optional model_overrides). No registration-trend input -- unlike
    statewide races, no per-district voter-registration dataset exists, so
    that adjustment simply isn't part of this breakdown (rather than always
    computing to a no-op 0 the way Ohio's empty registration_snapshots does
    for RACE_FUNDAMENTALS). Reuses incumbency_adjustment (with office="House",
    the smaller default bonus) and national_environment_adjustment unchanged
    -- only the historical-lean input differs from the statewide version.
    """
    as_of = as_of or date.today()
    model_overrides = district_fundamentals.get("model_overrides", {})
    # None means PVI wasn't scraped for this district -- degrades to a
    # neutral 0 (same no-fabrication convention as an empty house_elections
    # list) rather than crashing.
    pvi = district_fundamentals["pvi_dem_margin_pts"] or 0.0
    house_results = district_fundamentals["house_elections"]

    house = _recency_weighted_dem_margin(house_results, as_of, settings.presidential_election_half_life_years)
    combined = district_lean(pvi, house_results, as_of, model_overrides.get("district_pvi_weight"))
    inc = incumbency_adjustment(incumbent_party, office="House")
    env = national_environment_adjustment(approval_pct, president_party, generic_ballot_margin)
    total = combined + inc + env

    return DistrictFundamentalsBreakdown(
        district_pvi_lean_pts=pvi,
        district_house_lean_pts=house,
        combined_district_lean_pts=combined,
        incumbency_pts=inc,
        national_environment_pts=env,
        total_dem_margin_pts=total,
    )


def district_fundamentals_vote_share(
    district_fundamentals: dict,
    party: str,
    incumbent_party: str | None,
    approval_pct: float,
    president_party: str,
    as_of: date | None = None,
    generic_ballot_margin: float | None = None,
) -> float:
    """Projected two-party vote share for a House candidate of the given party."""
    margin = district_fundamentals_breakdown(
        district_fundamentals, incumbent_party, approval_pct, president_party, as_of, generic_ballot_margin
    ).total_dem_margin_pts
    if party == "Democratic":
        return 50 + margin / 2
    if party == "Republican":
        return 50 - margin / 2
    return 50.0


def poll_weight_for_election(
    election_date: date,
    as_of: date | None = None,
    floor: float | None = None,
    ceiling: float | None = None,
) -> float:
    """Fraction of weight given to polling (vs. fundamentals): a continuous
    exponential decay in days-to-election, approximating a hand-specified
    step schedule (~0.80 within 2 weeks, ~0.60 around 5 weeks out, ~0.40
    around 4 months out, asymptoting toward `poll_weight_floor` beyond that)
    without that schedule's discontinuous jumps. `floor`/`ceiling` default
    to the global settings but can be overridden per state (see
    RACE_FUNDAMENTALS[state_code]["model_overrides"]) for a race where
    real-time polling should count for much more than the standard curve
    gives it -- the decay *shape* (tau) stays the same either way, just
    shifted to a higher baseline."""
    as_of = as_of or date.today()
    days_to_election = max(0, (election_date - as_of).days)
    floor = floor if floor is not None else settings.poll_weight_floor
    ceiling = ceiling if ceiling is not None else settings.poll_weight_ceiling
    tau = settings.poll_weight_decay_tau_days
    return floor + (ceiling - floor) * math.exp(-days_to_election / tau)
