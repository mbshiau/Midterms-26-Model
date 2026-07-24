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
from datetime import date, timedelta

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
    office: str = "Governor",
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
            generic_ballot_margin, office,
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
        generic_ballot_margin, race.office,
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
            generic_ballot_margin, race.office,
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
                draws_sample=result.draws.tolist(),
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


def _snapshot_deltas(
    latest_rows: list[dict], baseline_rows: list[dict] | None
) -> list[dict] | None:
    if not baseline_rows:
        return None
    prior_by_candidate = {r["candidate_id"]: r["mean_vote_share"] for r in baseline_rows}
    deltas = []
    for r in latest_rows:
        prior = prior_by_candidate.get(r["candidate_id"])
        if prior is None:
            continue
        deltas.append({"name": r["name"], "party": r["party"], "delta": r["mean_vote_share"] - prior})
    deltas.sort(key=lambda d: d["delta"], reverse=True)
    return deltas or None


def race_movement_summary(db: Session, race: Race):
    """Powers the map page's "movers"/"closest races" list without shipping
    each race's full forecast history to the browser (see
    app.routers.races's /races/summary) -- that endpoint used to require the
    frontend to fetch every race's complete /forecast/history individually
    (N races x full snapshot history, including a fundamentals_breakdown
    blob per snapshot) just to derive a handful of vote-share deltas.

    Selects only the specific columns needed (never ForecastResult.
    draws_sample or ForecastSnapshot.fundamentals_breakdown, both of which
    forecast_history()/latest_forecast() pull in full for every snapshot),
    and only for the 2-3 snapshots actually used: latest, the one right
    before it (since-refresh), and the most recent one at least 7 days old
    (this-week) -- not the entire history.

    Returns (latest_created_at, latest_candidate_rows, since_refresh_deltas,
    this_week_deltas); latest_candidate_rows already sorted by mean vote
    share, descending. All four are None/[] when the race has no forecast
    yet.
    """
    snap_rows = (
        db.query(ForecastSnapshot.id, ForecastSnapshot.created_at)
        .filter(ForecastSnapshot.race_id == race.id)
        .order_by(ForecastSnapshot.created_at.asc())
        .all()
    )
    if not snap_rows:
        return None, [], None, None

    latest_id, latest_created_at = snap_rows[-1]
    baseline_id = snap_rows[-2][0] if len(snap_rows) >= 2 else None
    cutoff = latest_created_at - timedelta(days=7)
    eligible_week_ids = [sid for sid, ts in snap_rows if ts <= cutoff]
    week_baseline_id = eligible_week_ids[-1] if eligible_week_ids else None

    needed_ids = {latest_id}
    if baseline_id is not None:
        needed_ids.add(baseline_id)
    if week_baseline_id is not None:
        needed_ids.add(week_baseline_id)

    result_rows = (
        db.query(
            ForecastResult.snapshot_id,
            ForecastResult.candidate_id,
            ForecastResult.mean_vote_share,
            ForecastResult.win_probability,
            Candidate.name,
            Candidate.party,
        )
        .join(Candidate, ForecastResult.candidate_id == Candidate.id)
        .filter(ForecastResult.snapshot_id.in_(needed_ids))
        .all()
    )

    by_snapshot: dict[int, list[dict]] = {}
    for snapshot_id, candidate_id, mean_vote_share, win_probability, name, party in result_rows:
        by_snapshot.setdefault(snapshot_id, []).append(
            {
                "candidate_id": candidate_id,
                "name": name,
                "party": party,
                "mean_vote_share": mean_vote_share,
                "win_probability": win_probability,
            }
        )

    latest_rows = sorted(
        by_snapshot.get(latest_id, []), key=lambda r: r["mean_vote_share"], reverse=True
    )
    since_refresh = _snapshot_deltas(latest_rows, by_snapshot.get(baseline_id) if baseline_id else None)
    this_week = _snapshot_deltas(
        latest_rows, by_snapshot.get(week_baseline_id) if week_baseline_id else None
    )

    return latest_created_at, latest_rows, since_refresh, this_week
