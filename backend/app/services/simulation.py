"""Monte Carlo simulation engine.

Each candidate's vote share is drawn from Normal(weighted_mean, total_std),
where total_std combines poll-to-poll/sampling dispersion with a historical
polling-error term. Draws are clipped to [0, 100] and renormalized within
each simulation run so shares sum to 100 across modeled candidates; the
winner of a run is whoever has the largest normalized share.
"""

import math
from dataclasses import dataclass

import numpy as np

from app.services.weighting import CandidateAverage


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
) -> dict[int, CandidateSimulationResult]:
    if not candidate_averages:
        return {}

    rng = np.random.default_rng(seed)
    candidate_ids = list(candidate_averages.keys())

    raw_draws = []
    for cid in candidate_ids:
        avg = candidate_averages[cid]
        total_std = math.sqrt(avg.weighted_std**2 + historical_error_stdev**2)
        draws = rng.normal(loc=avg.weighted_mean, scale=total_std, size=n_simulations)
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


def histogram(draws: np.ndarray, n_bins: int = 30) -> tuple[list[float], list[int]]:
    counts, bin_edges = np.histogram(draws, bins=n_bins, range=(0, 100))
    return bin_edges.tolist(), counts.tolist()
