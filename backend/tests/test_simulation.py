from app.services.simulation import histogram, run_monte_carlo
from app.services.weighting import CandidateAverage


def test_run_monte_carlo_win_probabilities_favor_leading_candidate():
    averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=55.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=38.0, weighted_std=2.0, n_polls=3),
    }

    results = run_monte_carlo(averages, historical_error_stdev=4.0, n_simulations=10_000, seed=42)

    assert results[1].win_probability > 0.9
    assert results[1].win_probability + results[2].win_probability == 1.0
    assert results[1].mean_vote_share > results[2].mean_vote_share


def test_run_monte_carlo_draws_sum_to_100_per_run():
    averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=50.0, weighted_std=3.0, n_polls=2),
        2: CandidateAverage(candidate_id=2, weighted_mean=45.0, weighted_std=3.0, n_polls=2),
    }

    results = run_monte_carlo(averages, historical_error_stdev=4.0, n_simulations=1000, seed=1)

    totals = results[1].draws + results[2].draws
    assert all(abs(t - 100.0) < 1e-6 for t in totals)


def test_run_monte_carlo_close_race_is_closer_to_toss_up():
    averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=50.5, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=49.5, weighted_std=2.0, n_polls=3),
    }

    results = run_monte_carlo(averages, historical_error_stdev=4.0, n_simulations=10_000, seed=7)

    assert 0.3 < results[1].win_probability < 0.7


def test_histogram_shape():
    averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=55.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=39.0, weighted_std=2.0, n_polls=3),
    }
    results = run_monte_carlo(averages, historical_error_stdev=4.0, n_simulations=5000, seed=3)

    bin_edges, counts = histogram(results[1].draws, n_bins=30)

    assert len(bin_edges) == 31
    assert len(counts) == 30
    assert sum(counts) == 5000
    # candidate polls at ~55/(55+39)*100 ~= 58.5% two-party share; distribution
    # should have some spread, not collapse into a single bin
    assert sum(1 for c in counts if c > 0) > 1
