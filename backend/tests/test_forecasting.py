from datetime import date

from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Candidate
from app.services.forecasting import blend_with_fundamentals
from app.services.weighting import CandidateAverage

PA = RACE_FUNDAMENTALS["pa"]


def test_blend_is_a_linear_interpolation_between_polling_and_fundamentals():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=True)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=70.0, weighted_std=2.0, n_polls=5),
        2: CandidateAverage(candidate_id=2, weighted_mean=30.0, weighted_std=2.0, n_polls=5),
    }

    alpha = 0.8
    blended, fundamentals_shares = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], alpha, date(2026, 7, 10), 37.0, "Republican"
    )

    expected_dem_mean = alpha * 70.0 + (1 - alpha) * fundamentals_shares[1]
    assert abs(blended[1].weighted_mean - expected_dem_mean) < 1e-9

    # blended mean must sit strictly between the two pre-blend inputs
    # (this is a pure linear interpolation, unlike the post-simulation mean)
    lo, hi = sorted([70.0, fundamentals_shares[1]])
    assert lo <= blended[1].weighted_mean <= hi


def test_blend_widens_uncertainty_relative_to_polling_alone():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=True)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=55.0, weighted_std=1.0, n_polls=5),
        2: CandidateAverage(candidate_id=2, weighted_mean=45.0, weighted_std=1.0, n_polls=5),
    }

    blended, _ = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], 0.5, date(2026, 7, 10), 37.0, "Republican"
    )

    assert blended[1].weighted_std > polling_averages[1].weighted_std


def test_alpha_one_ignores_fundamentals_entirely():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=False)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=48.0, weighted_std=3.0, n_polls=2),
        2: CandidateAverage(candidate_id=2, weighted_mean=52.0, weighted_std=3.0, n_polls=2),
    }

    blended, _ = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], 1.0, date(2026, 7, 10), 37.0, "Republican"
    )

    assert blended[1].weighted_mean == polling_averages[1].weighted_mean
    assert blended[1].weighted_std == polling_averages[1].weighted_std
