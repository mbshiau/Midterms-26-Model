"""Monte Carlo simulation engine.

Each candidate's vote share is drawn from Normal(weighted_mean, total_std),
where total_std combines poll-to-poll/sampling dispersion with a historical
polling-error term. Draws are clipped to [0, 100] and renormalized within
each simulation run so shares sum to 100 across modeled candidates; the
winner of a run is whoever has the largest normalized share.

An optional `national_shock` (see `generate_national_shock`) adds a second,
*correlated* error component: a single shared Democratic-margin shift
applied to every candidate's draws at the same simulation-run index. Real
polling error is highly correlated across states -- if polls miss for one
party nationally, they tend to miss the same way almost everywhere at once,
not independently per state -- so treating every race's noise as fully
independent understates uncertainty. `generate_national_shock` derives its
seed purely from the calendar date, so every race simulated on the same day
shares the identical draw, regardless of processing order.
"""

import hashlib
import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from app.services.weighting import CandidateAverage


def _national_shock_seed(as_of: date) -> int:
    """Stable across process restarts (unlike Python's randomized hash()),
    so the same calendar date always derives the same seed."""
    digest = hashlib.sha256(as_of.isoformat().encode()).hexdigest()
    return int(digest, 16) % (2**32)


def generate_national_shock(n_simulations: int, stdev: float, as_of: date) -> np.ndarray:
    """A shared Democratic-margin shock (in points), one draw per simulation
    run index, identical for every race generated with the same `as_of`."""
    rng = np.random.default_rng(_national_shock_seed(as_of))
    return rng.normal(loc=0.0, scale=stdev, size=n_simulations)


@dataclass
class CandidateSimulationResult:
    candidate_id: int
    draws: np.ndarray
    mean_vote_share: float
    median_vote_share: float
    std_dev: float
    win_probability: float
    ci_low: float
    ci_high: float


def run_monte_carlo(
    candidate_averages: dict[int, CandidateAverage],
    historical_error_stdev: float,
    n_simulations: int,
    seed: int | None = None,
    candidate_parties: dict[int, str] | None = None,
    national_shock: np.ndarray | None = None,
) -> dict[int, CandidateSimulationResult]:
    if not candidate_averages:
        return {}

    rng = np.random.default_rng(seed)
    candidate_ids = list(candidate_averages.keys())
    candidate_parties = candidate_parties or {}
    if national_shock is None:
        national_shock = np.zeros(n_simulations)

    raw_draws = []
    for cid in candidate_ids:
        avg = candidate_averages[cid]
        total_std = math.sqrt(avg.weighted_std**2 + historical_error_stdev**2)
        draws = rng.normal(loc=avg.weighted_mean, scale=total_std, size=n_simulations)
        # A margin shock of `s` points is a vote-share shift of `s / 2` for
        # the party it favors and `-s / 2` for the other (margin = 2*share -
        # 100), applied identically at every simulation-run index so the two
        # candidates -- and every other race sharing this same array --
        # move together rather than independently.
        party = candidate_parties.get(cid)
        if party == "Democratic":
            draws = draws + national_shock / 2
        elif party == "Republican":
            draws = draws - national_shock / 2
        raw_draws.append(np.clip(draws, 0, 100))

    stacked = np.vstack(raw_draws)  # shape: (n_candidates, n_simulations)
    run_sums = stacked.sum(axis=0)
    run_sums[run_sums == 0] = 1e-9  # guard against degenerate all-zero draws
    normalized = stacked / run_sums * 100.0

    winner_idx = np.argmax(normalized, axis=0)

    results: dict[int, CandidateSimulationResult] = {}
    for i, cid in enumerate(candidate_ids):
        candidate_draws = normalized[i]
        win_probability = float(np.sum(winner_idx == i)) / n_simulations
        results[cid] = CandidateSimulationResult(
            candidate_id=cid,
            draws=candidate_draws,
            mean_vote_share=float(np.mean(candidate_draws)),
            median_vote_share=float(np.median(candidate_draws)),
            std_dev=float(np.std(candidate_draws)),
            win_probability=win_probability,
            ci_low=float(np.percentile(candidate_draws, 2.5)),
            ci_high=float(np.percentile(candidate_draws, 97.5)),
        )

    return results


def _scale_counts(counts: list[int], target_total: int) -> list[int]:
    """Rescales bucket counts to sum to exactly `target_total`, preserving
    the distribution's shape. Needed because `histogram` below only ever
    sees ForecastResult.draws_sample -- a capped random subsample (500 by
    default, see forecasting.DRAWS_SAMPLE_SIZE), not the full
    n_simulations draws it's a stand-in for -- so a plain bin count sums to
    the sample size, not the number of simulations actually run. A naive
    per-bin round (`count * scale`) would leave the total off by a few from
    accumulated rounding error; distributing the shortfall to the bins with
    the largest fractional remainder first (the standard "largest remainder"
    apportionment method) guarantees an exact match instead."""
    sample_total = sum(counts)
    if sample_total == 0 or sample_total == target_total:
        return counts
    scale = target_total / sample_total
    scaled = [c * scale for c in counts]
    floors = [int(x) for x in scaled]
    remainder = target_total - sum(floors)
    by_fractional_part_desc = sorted(range(len(scaled)), key=lambda i: scaled[i] - floors[i], reverse=True)
    for i in by_fractional_part_desc[:remainder]:
        floors[i] += 1
    return floors


def histogram(draws: np.ndarray, n_bins: int = 30, scale_to: int | None = None) -> tuple[list[float], list[int]]:
    """`scale_to` -- when given, rescales the bucket counts (see
    _scale_counts) so they sum to that total instead of len(draws); pass the
    snapshot's real n_simulations when `draws` is a capped sample rather
    than the full simulation output, so the histogram still reads as "out
    of n_simulations runs" rather than "out of however many happened to be
    stored"."""
    counts, bin_edges = np.histogram(draws, bins=n_bins, range=(0, 100))
    counts_list = counts.tolist()
    if scale_to is not None:
        counts_list = _scale_counts(counts_list, scale_to)
    return bin_edges.tolist(), counts_list
