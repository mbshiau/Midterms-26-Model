"""Ties weighted polling averages + the fundamentals model + Monte Carlo
simulation together and persists the result, scoped to a single Race.

The polling mean/std and the fundamentals mean are blended per candidate
before simulating, with the polling weight (alpha) following a continuous
exponential decay in days-to-election — from `poll_weight_floor` far out to
`poll_weight_ceiling` on election day (see
app.services.fundamentals.poll_weight_for_election). Both pre-blend
components are kept on each ForecastResult so the UI can show its
composition. A race's RACE_FUNDAMENTALS entry can carry an optional
"model_overrides" dict replacing poll_weight_floor/ceiling (and the
fundamentals-side weights -- see fundamentals.fundamentals_breakdown) for
that state specifically.

The fundamentals model's national-environment input blends presidential
approval with the generic congressional ballot (see
app.services.fundamentals.national_environment_adjustment /
app.services.generic_ballot).

The Monte Carlo step also layers in a correlated national polling-error
shock (see app.services.simulation.generate_national_shock), shared across
every race generated on the same as_of date, on top of each race's own
independent error term.

Kalshi market odds are deliberately NOT part of this blend -- they're
surfaced as their own standalone section (see app.routers.kalshi /
app.services.market_odds) rather than folded into the model's vote-share
estimate or win probability.
"""

import math
from dataclasses import asdict
from datetime import date

import numpy as np
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Candidate, ForecastResult, ForecastSnapshot, Poll, Race
from app.services import fundamentals
from app.services.approval import get_current_approval
from app.services.generic_ballot import get_current_generic_ballot
from app.services.pollster_ratings import get_pollster_ratings_by_name
from app.services.simulation import generate_national_shock, run_monte_carlo
from app.services.weighting import CandidateAverage, two_party_normalize, weighted_polling_averages

DRAWS_SAMPLE_SIZE = 2000


def _incumbent_party(candidates: list[Candidate]) -> str | None:
    for c in candidates:
        if c.incumbent:
            return c.party
    return None


def blend_with_fundamentals(
    race_fundamentals: dict,
    candidate_averages: dict[int, CandidateAverage],
    candidates: list[Candidate],
    alpha: float,
    as_of: date,
    approval_pct: float,
    president_party: str,
    generic_ballot_margin: float | None = None,
) -> tuple[dict[int, CandidateAverage], dict[int, float]]:
    """Returns (blended averages fed into the simulator, fundamentals share per candidate).

    Iterates over `candidates` rather than `candidate_averages` so a race
    with zero polls yet (no real polling published for the matchup) still
    produces a full fundamentals-only forecast instead of an empty result --
    real-data-only means never fabricating a poll, not refusing to forecast
    at all when none exist yet.
    """
    incumbent_party = _incumbent_party(candidates)
    fundamentals_shares: dict[int, float] = {}
    blended: dict[int, CandidateAverage] = {}

    for candidate in candidates:
        fundamentals_share = fundamentals.fundamentals_vote_share(
            race_fundamentals, candidate.party, incumbent_party, approval_pct, president_party, as_of,
            generic_ballot_margin,
        )
        fundamentals_shares[candidate.id] = fundamentals_share

        avg = candidate_averages.get(candidate.id)
        if avg is None:
            # No polling exists for this candidate -- alpha is expected to
            # be 0 here (see generate_forecast), so the blend is just the
            # fundamentals estimate with the fundamentals-only uncertainty.
            blended_mean = fundamentals_share
            blended_std = settings.fundamentals_uncertainty_stdev
            n_polls = 0
        else:
            blended_mean = alpha * avg.weighted_mean + (1 - alpha) * fundamentals_share
            blended_std = math.sqrt(
                (alpha * avg.weighted_std) ** 2
                + ((1 - alpha) * settings.fundamentals_uncertainty_stdev) ** 2
            )
            n_polls = avg.n_polls

        blended[candidate.id] = CandidateAverage(
            candidate_id=candidate.id,
            weighted_mean=blended_mean,
            weighted_std=blended_std,
            n_polls=n_polls,
        )

    return blended, fundamentals_shares


def generate_forecast(
    db: Session,
    race: Race,
    n_simulations: int | None = None,
    recency_half_life_days: float | None = None,
    historical_error_stdev: float | None = None,
    as_of: date | None = None,
    seed: int | None = None,
) -> ForecastSnapshot:
    n_simulations = n_simulations or settings.default_n_simulations
    half_life_days = recency_half_life_days or settings.recency_half_life_days
    error_stdev = historical_error_stdev or settings.historical_error_stdev
    as_of = as_of or date.today()

    polls = (
        db.query(Poll)
        .filter(Poll.race_id == race.id)
        .options(selectinload(Poll.results))
        .all()
    )

    candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
    fundamentals_data = RACE_FUNDAMENTALS[race.state_code]

    pollster_ratings = get_pollster_ratings_by_name(db)
    polling_averages = two_party_normalize(
        weighted_polling_averages(polls, as_of, half_life_days, pollster_ratings)
    )

    approval = get_current_approval(db)
    generic_ballot = get_current_generic_ballot(db)
    generic_ballot_margin = generic_ballot.dem_pct - generic_ballot.rep_pct
    # No real polling exists yet for this race's matchup -- force 0% polling
    # weight (100% fundamentals) rather than reporting the normal alpha
    # curve's value, which would misleadingly imply polls are contributing
    # to a blend that, in reality, has none to draw on.
    model_overrides = fundamentals_data.get("model_overrides", {})
    alpha = (
        fundamentals.poll_weight_for_election(
            race.election_date,
            as_of,
            floor=model_overrides.get("poll_weight_floor"),
            ceiling=model_overrides.get("poll_weight_ceiling"),
        )
        if polls
        else 0.0
    )
    blended_averages, fundamentals_shares = blend_with_fundamentals(
        fundamentals_data, polling_averages, candidates, alpha, as_of, approval.approval_pct, approval.party,
        generic_ballot_margin,
    )

    # Shared across every race generated with this same as_of date -- see
    # app.services.simulation.generate_national_shock -- so a correlated
    # national polling miss moves every state's simulation together instead
    # of each race drawing fully independent noise.
    national_shock = generate_national_shock(n_simulations, settings.national_error_stdev, as_of)
    candidate_parties = {c.id: c.party for c in candidates}
    sim_results = run_monte_carlo(
        blended_averages,
        error_stdev,
        n_simulations,
        seed=seed,
        candidate_parties=candidate_parties,
        national_shock=national_shock,
    )

    incumbent_party = _incumbent_party(candidates)
    breakdown = asdict(
        fundamentals.fundamentals_breakdown(
            fundamentals_data, incumbent_party, approval.approval_pct, approval.party, as_of,
            generic_ballot_margin,
        )
    )
    breakdown["president_name"] = approval.name
    breakdown["president_approval_pct"] = approval.approval_pct
    breakdown["president_approval_as_of"] = approval.as_of.isoformat()
    breakdown["president_approval_source_url"] = approval.source_url
    breakdown["generic_ballot_dem_pct"] = generic_ballot.dem_pct
    breakdown["generic_ballot_rep_pct"] = generic_ballot.rep_pct
    breakdown["generic_ballot_as_of"] = generic_ballot.as_of.isoformat()
    breakdown["generic_ballot_source_url"] = generic_ballot.source_url
    # Most states use the last 3 elections per race type, but a state can
    # have fewer (e.g. an outlier year discarded rather than backfilled) --
    # exposing the actual count keeps the UI's "(last N races)" labels
    # honest instead of hardcoding "3" everywhere.
    breakdown["gubernatorial_elections_count"] = len(fundamentals_data["gubernatorial_elections"])
    breakdown["senate_elections_count"] = len(fundamentals_data["senate_elections"])
    breakdown["presidential_elections_count"] = len(fundamentals_data["presidential_elections"])

    snapshot = ForecastSnapshot(
        race_id=race.id,
        n_simulations=n_simulations,
        n_polls_used=len(polls),
        poll_weight_alpha=alpha,
        fundamentals_breakdown=breakdown,
    )
    db.add(snapshot)
    db.flush()

    for candidate_id, result in sim_results.items():
        sample = np.random.default_rng(seed).choice(
            result.draws, size=min(DRAWS_SAMPLE_SIZE, len(result.draws)), replace=False
        )
        db.add(
            ForecastResult(
                snapshot_id=snapshot.id,
                candidate_id=candidate_id,
                mean_vote_share=result.mean_vote_share,
                median_vote_share=result.median_vote_share,
                std_dev=result.std_dev,
                win_probability=result.win_probability,
                ci_low=result.ci_low,
                ci_high=result.ci_high,
                draws_sample=sample.tolist(),
                # No polling-only figure exists when the race has zero real
                # polls yet -- fall back to the fundamentals share so the
                # (non-nullable) column still holds a real, non-fabricated
                # number rather than a fictitious polling estimate.
                polling_vote_share=(
                    polling_averages[candidate_id].weighted_mean
                    if candidate_id in polling_averages
                    else fundamentals_shares[candidate_id]
                ),
                fundamentals_vote_share=fundamentals_shares[candidate_id],
            )
        )

    db.commit()
    db.refresh(snapshot)
    return snapshot


def latest_forecast(db: Session, race: Race) -> ForecastSnapshot | None:
    return (
        db.query(ForecastSnapshot)
        .filter(ForecastSnapshot.race_id == race.id)
        .options(selectinload(ForecastSnapshot.results))
        .order_by(ForecastSnapshot.created_at.desc())
        .first()
    )


def forecast_history(db: Session, race: Race) -> list[ForecastSnapshot]:
    return (
        db.query(ForecastSnapshot)
        .filter(ForecastSnapshot.race_id == race.id)
        .options(selectinload(ForecastSnapshot.results))
        .order_by(ForecastSnapshot.created_at.asc())
        .all()
    )
