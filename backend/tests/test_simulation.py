from datetime import date

import numpy as np

from app.services.simulation import generate_national_shock, histogram, run_monte_carlo
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


def test_generate_national_shock_is_deterministic_by_date():
    a = generate_national_shock(10_000, stdev=3.0, as_of=date(2026, 7, 15))
    b = generate_national_shock(10_000, stdev=3.0, as_of=date(2026, 7, 15))
    assert np.array_equal(a, b)


def test_generate_national_shock_differs_across_dates():
    a = generate_national_shock(10_000, stdev=3.0, as_of=date(2026, 7, 15))
    b = generate_national_shock(10_000, stdev=3.0, as_of=date(2026, 7, 16))
    assert not np.array_equal(a, b)


def test_generate_national_shock_has_the_requested_stdev_and_is_centered_on_zero():
    shock = generate_national_shock(200_000, stdev=3.0, as_of=date(2026, 7, 15))
    assert abs(np.mean(shock)) < 0.05
    assert abs(np.std(shock) - 3.0) < 0.05


def test_national_shock_pushes_the_democratic_candidate_up_and_republican_down():
    averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=50.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=50.0, weighted_std=2.0, n_polls=3),
    }
    parties = {1: "Democratic", 2: "Republican"}

    no_shock = run_monte_carlo(averages, historical_error_stdev=4.0, n_simulations=20_000, seed=1)
    positive_shock = np.full(20_000, 6.0)  # a uniformly Dem-favorable national miss
    with_shock = run_monte_carlo(
        averages, historical_error_stdev=4.0, n_simulations=20_000, seed=1,
        candidate_parties=parties, national_shock=positive_shock,
    )

    assert with_shock[1].mean_vote_share > no_shock[1].mean_vote_share
    assert with_shock[2].mean_vote_share < no_shock[2].mean_vote_share


def test_national_shock_correlates_two_otherwise_independent_races():
    # The actual point of this feature: two different races, simulated with
    # the same shared national_shock array, must move *together* across
    # simulation runs -- not just each individually widen -- since real
    # polling error is correlated across states, not independent per state.
    race_a = {
        1: CandidateAverage(candidate_id=1, weighted_mean=51.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=49.0, weighted_std=2.0, n_polls=3),
    }
    race_b = {
        3: CandidateAverage(candidate_id=3, weighted_mean=48.0, weighted_std=2.0, n_polls=3),
        4: CandidateAverage(candidate_id=4, weighted_mean=52.0, weighted_std=2.0, n_polls=3),
    }
    parties_a = {1: "Democratic", 2: "Republican"}
    parties_b = {3: "Democratic", 4: "Republican"}
    # A deliberately large stdev here (vs. the production default of 3.0) so
    # the shared-shock effect dominates idiosyncratic noise enough to produce
    # an unambiguous, easy-to-assert correlation signal -- this test proves
    # the *mechanism* works, independent of the production tuning value.
    shock = generate_national_shock(50_000, stdev=15.0, as_of=date(2026, 7, 15))

    # Different seeds for the idiosyncratic noise -- only the shared shock
    # should induce any correlation between these two otherwise-unrelated races.
    result_a = run_monte_carlo(
        race_a, historical_error_stdev=4.0, n_simulations=50_000, seed=11,
        candidate_parties=parties_a, national_shock=shock,
    )
    result_b = run_monte_carlo(
        race_b, historical_error_stdev=4.0, n_simulations=50_000, seed=22,
        candidate_parties=parties_b, national_shock=shock,
    )

    correlation = np.corrcoef(result_a[1].draws, result_b[3].draws)[0, 1]
    assert correlation > 0.5


def test_without_a_shock_two_races_are_uncorrelated():
    # Regression guard for the pre-existing (still-default) behavior: with
    # no national_shock passed, independent races must NOT be correlated.
    race_a = {
        1: CandidateAverage(candidate_id=1, weighted_mean=51.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=49.0, weighted_std=2.0, n_polls=3),
    }
    race_b = {
        3: CandidateAverage(candidate_id=3, weighted_mean=48.0, weighted_std=2.0, n_polls=3),
        4: CandidateAverage(candidate_id=4, weighted_mean=52.0, weighted_std=2.0, n_polls=3),
    }

    result_a = run_monte_carlo(race_a, historical_error_stdev=4.0, n_simulations=50_000, seed=11)
    result_b = run_monte_carlo(race_b, historical_error_stdev=4.0, n_simulations=50_000, seed=22)

    correlation = np.corrcoef(result_a[1].draws, result_b[3].draws)[0, 1]
    assert abs(correlation) < 0.05


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
