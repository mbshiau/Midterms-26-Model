"""Weighted polling average: recency (half-life decay) x sample-size x
pollster-quality weighting."""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.models import Poll, PollsterRating
from app.services.pollster_ratings import normalize_pollster_name, pollster_quality_weight


@dataclass
class CandidateAverage:
    candidate_id: int
    weighted_mean: float
    weighted_std: float
    n_polls: int


def poll_weight(
    poll: Poll,
    as_of: date,
    half_life_days: float,
    pollster_ratings: dict[str, PollsterRating] | None = None,
) -> float:
    days_old = max((as_of - poll.field_end_date).days, 0)
    recency_weight = 0.5 ** (days_old / half_life_days) if half_life_days > 0 else 1.0
    sample_weight = math.sqrt(poll.sample_size)

    # `pollster_ratings` is optional and defaults to an empty lookup, so a
    # pollster with no rating on file (or no ratings fetched at all yet)
    # gets a neutral 1.0 multiplier here -- byte-for-byte the same as before
    # this weighting existed, not a penalty for being untracked.
    rating = (pollster_ratings or {}).get(normalize_pollster_name(poll.pollster))
    quality_weight = pollster_quality_weight(rating.avg_error_pts if rating else None)

    return recency_weight * sample_weight * quality_weight


def two_party_normalize(
    candidate_averages: dict[int, CandidateAverage],
) -> dict[int, CandidateAverage]:
    """Rescales weighted means so they sum to 100 across candidates.

    Raw poll pct's leave a residual for undecided/other, so the weighted mean
    understates each candidate's two-party share — putting it on a different
    scale than the fundamentals model's (which is inherently two-party). This
    puts both on the same footing before they're blended or compared.
    """
    total = sum(avg.weighted_mean for avg in candidate_averages.values())
    if total == 0:
        return candidate_averages
    return {
        candidate_id: CandidateAverage(
            candidate_id=candidate_id,
            weighted_mean=avg.weighted_mean / total * 100,
            weighted_std=avg.weighted_std,
            n_polls=avg.n_polls,
        )
        for candidate_id, avg in candidate_averages.items()
    }


def poll_weights(
    polls: list[Poll],
    as_of: date,
    half_life_days: float,
    pollster_ratings: dict[str, PollsterRating] | None = None,
) -> dict[int, float]:
    """Each poll's raw weight normalized to a 0-1 share of total influence
    on the polling average — surfaced to users as a transparency signal."""
    raw = {poll.id: poll_weight(poll, as_of, half_life_days, pollster_ratings) for poll in polls}
    total = sum(raw.values())
    if total == 0:
        return {poll_id: 0.0 for poll_id in raw}
    return {poll_id: w / total for poll_id, w in raw.items()}


def weighted_polling_averages(
    polls: list[Poll],
    as_of: date,
    half_life_days: float,
    pollster_ratings: dict[str, PollsterRating] | None = None,
) -> dict[int, CandidateAverage]:
    """Per-candidate weighted mean vote share and poll-to-poll dispersion.

    When only one poll exists for a candidate, dispersion falls back to the
    binomial sampling-error estimate for that poll instead of a (undefined)
    poll-to-poll standard deviation.
    """
    per_candidate: dict[int, list[tuple[float, float, int]]] = {}
    for poll in polls:
        w = poll_weight(poll, as_of, half_life_days, pollster_ratings)
        for result in poll.results:
            per_candidate.setdefault(result.candidate_id, []).append(
                (result.pct, w, poll.sample_size)
            )

    out: dict[int, CandidateAverage] = {}
    for candidate_id, rows in per_candidate.items():
        pcts = np.array([r[0] for r in rows])
        weights = np.array([r[1] for r in rows])
        weighted_mean = float(np.average(pcts, weights=weights))

        if len(rows) > 1:
            variance = float(np.average((pcts - weighted_mean) ** 2, weights=weights))
            weighted_std = math.sqrt(variance)
        else:
            p = weighted_mean / 100.0
            n = rows[0][2]
            weighted_std = math.sqrt(p * (1 - p) / n) * 100.0

        out[candidate_id] = CandidateAverage(
            candidate_id=candidate_id,
            weighted_mean=weighted_mean,
            weighted_std=weighted_std,
            n_polls=len(rows),
        )

    return out
