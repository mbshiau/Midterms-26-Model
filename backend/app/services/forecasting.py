"""Ties weighted polling averages + the fundamentals model + Monte Carlo
simulation together and persists the result, scoped to a single Race.

The polling mean/std and the fundamentals mean are blended per candidate
before simulating, with the polling weight (alpha) following a continuous
exponential decay in days-to-election — from `poll_weight_floor` far out to
`poll_weight_ceiling` on election day (see
app.services.fundamentals.poll_weight_for_election). Both pre-blend
components are kept on each ForecastResult so the UI can show its
composition.
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
from app.services.simulation import run_monte_carlo
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
) -> tuple[dict[int, CandidateAverage], dict[int, float]]:
    """Returns (blended averages fed into the simulator, fundamentals share per candidate)."""
    incumbent_party = _incumbent_party(candidates)
    by_id = {c.id: c for c in candidates}
    fundamentals_shares: dict[int, float] = {}
    blended: dict[int, CandidateAverage] = {}

    for candidate_id, avg in candidate_averages.items():
        candidate = by_id[candidate_id]
        fundamentals_share = fundamentals.fundamentals_vote_share(
            race_fundamentals, candidate.party, incumbent_party, approval_pct, president_party, as_of
        )
        fundamentals_shares[candidate_id] = fundamentals_share

        blended_mean = alpha * avg.weighted_mean + (1 - alpha) * fundamentals_share
        blended_std = math.sqrt(
            (alpha * avg.weighted_std) ** 2
            + ((1 - alpha) * settings.fundamentals_uncertainty_stdev) ** 2
        )
        blended[candidate_id] = CandidateAverage(
            candidate_id=candidate_id,
            weighted_mean=blended_mean,
            weighted_std=blended_std,
            n_polls=avg.n_polls,
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
    if not polls:
        raise ValueError(f"no polls available to forecast {race.state_code} from")

    candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
    fundamentals_data = RACE_FUNDAMENTALS[race.state_code]

    polling_averages = two_party_normalize(weighted_polling_averages(polls, as_of, half_life_days))

    approval = get_current_approval(db)
    alpha = fundamentals.poll_weight_for_election(race.election_date, as_of)
    blended_averages, fundamentals_shares = blend_with_fundamentals(
        fundamentals_data, polling_averages, candidates, alpha, as_of, approval.approval_pct, approval.party
    )

    sim_results = run_monte_carlo(blended_averages, error_stdev, n_simulations, seed=seed)

    incumbent_party = _incumbent_party(candidates)
    breakdown = asdict(
        fundamentals.fundamentals_breakdown(
            fundamentals_data, incumbent_party, approval.approval_pct, approval.party, as_of
        )
    )
    breakdown["president_name"] = approval.name
    breakdown["president_approval_pct"] = approval.approval_pct
    breakdown["president_approval_as_of"] = approval.as_of.isoformat()
    breakdown["president_approval_source_url"] = approval.source_url

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
                polling_vote_share=polling_averages[candidate_id].weighted_mean,
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
