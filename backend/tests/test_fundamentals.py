from datetime import date

from app.services import fundamentals


def test_gubernatorial_lean_favors_democratic_given_researched_data():
    # PA has leaned Democratic in 5 of the last 6 gubernatorial races.
    lean = fundamentals.gubernatorial_lean(as_of=date(2026, 7, 10))
    assert lean > 0


def test_presidential_lean_is_close_to_even_given_researched_data():
    # PA's last 6 presidential races have been close swing-state results.
    lean = fundamentals.presidential_lean(as_of=date(2026, 7, 10))
    assert -5 < lean < 5


def test_more_recent_elections_are_weighted_more_heavily():
    # 2022 (D+12.5) is the most recent governor race; 2010 (R+9.0) is older.
    # A shorter half-life should pull the blended lean further toward the
    # more recent result.
    short_half_life_lean = fundamentals._recency_weighted_dem_margin(
        fundamentals.GUBERNATORIAL_ELECTIONS, date(2026, 7, 10), half_life_years=4.0
    )
    long_half_life_lean = fundamentals._recency_weighted_dem_margin(
        fundamentals.GUBERNATORIAL_ELECTIONS, date(2026, 7, 10), half_life_years=40.0
    )
    # short half-life (recency dominates) should sit closer to the most
    # recent election's margin than the long half-life (nearly unweighted) does
    most_recent_margin = 2 * fundamentals.GUBERNATORIAL_ELECTIONS[-1]["dem_share"] - 100
    assert abs(short_half_life_lean - most_recent_margin) < abs(
        long_half_life_lean - most_recent_margin
    )


def test_combined_historical_lean_blends_both_series_by_configured_weight():
    as_of = date(2026, 7, 10)
    gub = fundamentals.gubernatorial_lean(as_of)
    pres = fundamentals.presidential_lean(as_of)
    combined = fundamentals.combined_historical_lean(as_of)
    w = fundamentals.settings.gubernatorial_lean_weight

    assert abs(combined - (w * gub + (1 - w) * pres)) < 1e-9
    # blended value must land between the two component leans
    lo, hi = sorted([gub, pres])
    assert lo <= combined <= hi


def test_incumbency_adjustment_sign():
    assert fundamentals.incumbency_adjustment("Democratic") > 0
    assert fundamentals.incumbency_adjustment("Republican") < 0
    assert fundamentals.incumbency_adjustment(None) == 0


def test_national_environment_favors_out_party_when_approval_low():
    adjustment = fundamentals.national_environment_adjustment(
        approval_pct=37.0, president_party="Republican"
    )
    assert adjustment > 0

    # symmetric: a Democratic president at the same approval favors Republicans
    adjustment_dem_pres = fundamentals.national_environment_adjustment(
        approval_pct=37.0, president_party="Democratic"
    )
    assert adjustment_dem_pres < 0


def test_fundamentals_vote_share_is_zero_sum_between_two_parties():
    dem_share = fundamentals.fundamentals_vote_share(
        "Democratic", "Democratic", approval_pct=37.0, president_party="Republican"
    )
    rep_share = fundamentals.fundamentals_vote_share(
        "Republican", "Democratic", approval_pct=37.0, president_party="Republican"
    )
    assert abs((dem_share + rep_share) - 100) < 1e-9
    assert dem_share > rep_share


def test_poll_weight_reaches_ceiling_on_election_day():
    weight = fundamentals.poll_weight_for_election(as_of=fundamentals.ELECTION_DATE)
    assert weight == fundamentals.settings.poll_weight_ceiling


def test_poll_weight_approaches_floor_far_out():
    weight = fundamentals.poll_weight_for_election(as_of=date(2025, 1, 1))  # >600 days out
    assert abs(weight - fundamentals.settings.poll_weight_floor) < 0.01


def test_poll_weight_decreases_monotonically_with_days_to_election():
    close = fundamentals.poll_weight_for_election(as_of=date(2026, 10, 30))  # T=4
    mid = fundamentals.poll_weight_for_election(as_of=date(2026, 9, 1))  # T=63
    far = fundamentals.poll_weight_for_election(as_of=date(2026, 1, 1))  # T=306

    assert (
        fundamentals.settings.poll_weight_floor
        < far
        < mid
        < close
        <= fundamentals.settings.poll_weight_ceiling
    )


def test_poll_weight_approximates_the_proposed_schedule_anchor_points():
    # Continuous curve fit to roughly track a hand-specified step schedule
    # (~0.80 within 2 weeks, ~0.60 around 5 weeks, ~0.40 around 4 months)
    # without that schedule's discontinuous jumps. Loose tolerances since
    # matching a step function's flat plateaus exactly isn't the point.
    two_weeks_out = fundamentals.poll_weight_for_election(as_of=date(2026, 10, 20))
    five_weeks_out = fundamentals.poll_weight_for_election(as_of=date(2026, 9, 26))
    four_months_out = fundamentals.poll_weight_for_election(as_of=date(2026, 7, 3))

    assert abs(two_weeks_out - 0.80) < 0.1
    assert abs(five_weeks_out - 0.60) < 0.1
    assert abs(four_months_out - 0.40) < 0.1
