from datetime import date

from app.models import PollsterRating, Poll, PollResult, Population
from app.services.weighting import (
    CandidateAverage,
    poll_weight,
    poll_weights,
    two_party_normalize,
    weighted_polling_averages,
)


def make_rating(pollster_name: str, avg_error_pts: float) -> PollsterRating:
    return PollsterRating(
        pollster_name=pollster_name,
        normalized_name=pollster_name.strip().lower(),
        avg_error_pts=avg_error_pts,
        source_url="https://pollingsource.com/pollsters",
    )


def make_poll(
    field_end_date, sample_size, results: dict[int, float], poll_id: int = 0, pollster: str = "Test Pollster"
) -> Poll:
    poll = Poll(
        id=poll_id,
        pollster=pollster,
        field_start_date=field_end_date,
        field_end_date=field_end_date,
        release_date=field_end_date,
        sample_size=sample_size,
        population=Population.RV,
        margin_of_error=3.0,
        undecided_pct=0.0,
        source_url="https://example.com",
    )
    poll.results = [
        PollResult(candidate_id=cid, pct=pct) for cid, pct in results.items()
    ]
    return poll


def test_poll_weight_decays_with_age():
    as_of = date(2026, 7, 10)
    fresh = make_poll(date(2026, 7, 9), 1000, {1: 50.0})
    old = make_poll(date(2026, 1, 1), 1000, {1: 50.0})

    assert poll_weight(fresh, as_of, half_life_days=21) > poll_weight(old, as_of, half_life_days=21)


def test_poll_weight_increases_with_sample_size():
    as_of = date(2026, 7, 10)
    small = make_poll(as_of, 400, {1: 50.0})
    large = make_poll(as_of, 1600, {1: 50.0})

    assert poll_weight(large, as_of, half_life_days=21) > poll_weight(small, as_of, half_life_days=21)


def test_weighted_average_single_poll_uses_sampling_error_fallback():
    as_of = date(2026, 7, 10)
    poll = make_poll(as_of, 1000, {1: 55.0, 2: 39.0})

    averages = weighted_polling_averages([poll], as_of, half_life_days=21)

    assert averages[1].weighted_mean == 55.0
    assert averages[1].n_polls == 1
    assert averages[1].weighted_std > 0


def test_weighted_average_multiple_polls_weights_recent_more_heavily():
    as_of = date(2026, 7, 10)
    old_poll = make_poll(date(2026, 1, 1), 1000, {1: 40.0})
    recent_poll = make_poll(date(2026, 7, 1), 1000, {1: 60.0})

    averages = weighted_polling_averages([old_poll, recent_poll], as_of, half_life_days=21)

    # recency weighting should pull the average closer to the recent poll than
    # a naive unweighted mean of 50.0
    assert averages[1].weighted_mean > 50.0
    assert averages[1].n_polls == 2


def test_poll_weights_normalize_to_one_and_favor_recent_larger_polls():
    as_of = date(2026, 7, 10)
    old_small = make_poll(date(2026, 1, 1), 400, {1: 50.0}, poll_id=1)
    recent_large = make_poll(date(2026, 7, 9), 1600, {1: 50.0}, poll_id=2)

    weights = poll_weights([old_small, recent_large], as_of, half_life_days=21)

    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights[2] > weights[1]


def test_two_party_normalize_rescales_to_sum_100_preserving_ratio():
    raw = {
        1: CandidateAverage(candidate_id=1, weighted_mean=50.0, weighted_std=2.0, n_polls=3),
        2: CandidateAverage(candidate_id=2, weighted_mean=30.0, weighted_std=2.0, n_polls=3),
    }

    normalized = two_party_normalize(raw)

    assert abs(sum(a.weighted_mean for a in normalized.values()) - 100.0) < 1e-9
    # the ratio between candidates is preserved, only the scale changes
    assert abs(normalized[1].weighted_mean / normalized[2].weighted_mean - 50.0 / 30.0) < 1e-9
    # std is left as an absolute percentage-point dispersion, unrescaled
    assert normalized[1].weighted_std == raw[1].weighted_std


def test_poll_weight_upweights_a_higher_quality_pollster():
    as_of = date(2026, 7, 10)
    good_poll = make_poll(as_of, 1000, {1: 50.0}, pollster="Great Pollster")
    bad_poll = make_poll(as_of, 1000, {1: 50.0}, pollster="Bad Pollster")
    ratings = {
        "great pollster": make_rating("Great Pollster", avg_error_pts=1.0),
        "bad pollster": make_rating("Bad Pollster", avg_error_pts=20.0),
    }

    good_weight = poll_weight(good_poll, as_of, half_life_days=21, pollster_ratings=ratings)
    bad_weight = poll_weight(bad_poll, as_of, half_life_days=21, pollster_ratings=ratings)

    assert good_weight > bad_weight


def test_poll_weight_matches_pollster_name_case_and_whitespace_insensitively():
    as_of = date(2026, 7, 10)
    poll = make_poll(as_of, 1000, {1: 50.0}, pollster="  YouGov  ")
    ratings = {"yougov": make_rating("YouGov", avg_error_pts=1.0)}

    with_rating = poll_weight(poll, as_of, half_life_days=21, pollster_ratings=ratings)
    without_rating = poll_weight(poll, as_of, half_life_days=21, pollster_ratings=None)

    assert with_rating > without_rating


def test_poll_weight_is_unchanged_for_an_untracked_pollster():
    as_of = date(2026, 7, 10)
    poll = make_poll(as_of, 1000, {1: 50.0}, pollster="Some New Outfit")
    ratings = {"yougov": make_rating("YouGov", avg_error_pts=1.0)}

    tracked_missing = poll_weight(poll, as_of, half_life_days=21, pollster_ratings=ratings)
    no_ratings_at_all = poll_weight(poll, as_of, half_life_days=21, pollster_ratings=None)

    assert tracked_missing == no_ratings_at_all


def test_weighted_polling_averages_pulls_toward_the_higher_quality_pollster():
    as_of = date(2026, 7, 10)
    good_poll = make_poll(as_of, 1000, {1: 60.0}, poll_id=1, pollster="Great Pollster")
    bad_poll = make_poll(as_of, 1000, {1: 40.0}, poll_id=2, pollster="Bad Pollster")
    ratings = {
        "great pollster": make_rating("Great Pollster", avg_error_pts=1.0),
        "bad pollster": make_rating("Bad Pollster", avg_error_pts=20.0),
    }

    averages = weighted_polling_averages([good_poll, bad_poll], as_of, half_life_days=21, pollster_ratings=ratings)

    # An unweighted mean of 60/40 would land exactly on 50 -- pollster quality
    # weighting should pull it toward the more accurate pollster's 60.
    assert averages[1].weighted_mean > 50.0
