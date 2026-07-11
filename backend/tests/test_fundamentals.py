from datetime import date

from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.services import fundamentals

PA = RACE_FUNDAMENTALS["pa"]
OH = RACE_FUNDAMENTALS["oh"]
GA = RACE_FUNDAMENTALS["ga"]
ME = RACE_FUNDAMENTALS["me"]
IA = RACE_FUNDAMENTALS["ia"]


def test_gubernatorial_lean_favors_democratic_given_researched_data():
    # PA has leaned Democratic in all of the last 3 gubernatorial races.
    lean = fundamentals.gubernatorial_lean(PA["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_senate_lean_favors_democratic_given_researched_data():
    # PA's last 3 Senate races: Casey '18 (D+13.4), Fetterman '22 (D+5.0),
    # McCormick '24 (R+0.4) — net Democratic given recency weighting still
    # favors the two clearer Democratic wins.
    lean = fundamentals.senate_lean(PA["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_presidential_lean_is_close_to_even_given_researched_data():
    # PA's last 3 presidential races have been close swing-state results.
    lean = fundamentals.presidential_lean(PA["presidential_elections"], as_of=date(2026, 7, 10))
    assert -5 < lean < 5


def test_ohio_gubernatorial_lean_favors_republican():
    # Ohio's last 3 governor races: Kasich '14 (R+32), DeWine open-seat '18
    # (close), DeWine '22 (R+25.6) — solidly Republican on net.
    lean = fundamentals.gubernatorial_lean(OH["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_ohio_senate_lean_favors_republican():
    # Brown '18 (D win) but Vance '22 and Moreno '24 both Republican, and
    # more recent, so the net recency-weighted lean tilts Republican.
    lean = fundamentals.senate_lean(OH["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_ohio_presidential_lean_favors_republican():
    # Ohio is no longer a swing state at the presidential level.
    lean = fundamentals.presidential_lean(OH["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_georgia_gubernatorial_lean_favors_republican():
    # Kemp/Deal have won all 3 of the last GA governor races, though not by
    # huge margins (2018 was decided by ~1.4 points).
    lean = fundamentals.gubernatorial_lean(GA["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_georgia_senate_lean_favors_democratic():
    # All 3 of the last GA Senate races (Ossoff, Warnock x2) went Democratic,
    # each narrowly.
    lean = fundamentals.senate_lean(GA["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_georgia_presidential_lean_is_close_to_even():
    # Georgia has been the closest kind of swing state this decade.
    lean = fundamentals.presidential_lean(GA["presidential_elections"], as_of=date(2026, 7, 10))
    assert -5 < lean < 5


def test_georgia_has_no_registration_data_either():
    # Georgia doesn't register voters by party (open primaries).
    assert fundamentals.registration_trend_adjustment(GA["registration_snapshots"]) == 0.0


def test_maine_gubernatorial_lean_favors_democratic():
    # Mills won the last 2 of 3 Maine governor races, each more comfortably
    # than LePage's 2014 win, so the recency-weighted lean is Democratic.
    lean = fundamentals.gubernatorial_lean(ME["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_maine_senate_lean_favors_democratic():
    # King (I, caucuses D) won 2018/2024 by wide margins with the Democratic
    # nominee's share folded in; Collins (R) won 2020. Net recency-weighted
    # lean still favors the Democratic-aligned side.
    lean = fundamentals.senate_lean(ME["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_maine_presidential_lean_favors_democratic():
    # Maine has gone Democratic statewide in each of the last 3 presidential
    # races, by a wider margin than PA/GA's toss-up range.
    lean = fundamentals.presidential_lean(ME["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_maine_has_no_usable_registration_trend():
    # Maine does register voters by party, but only one reliably-sourced
    # snapshot was found -- not enough points for a trend, so it's a no-op
    # the same way OH/GA's genuinely-untracked empty lists are.
    assert fundamentals.registration_trend_adjustment(ME["registration_snapshots"]) == 0.0


def test_iowa_gubernatorial_lean_favors_republican():
    # Reynolds/Branstad have won all 3 of the last Iowa governor races,
    # each by double digits in raw terms.
    lean = fundamentals.gubernatorial_lean(IA["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_iowa_senate_lean_favors_republican():
    # Grassley and Ernst have won all 3 of the last Iowa Senate races.
    lean = fundamentals.senate_lean(IA["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_iowa_presidential_lean_favors_republican():
    # Iowa has voted for Trump by comfortable margins in each of the last 3
    # presidential races -- no longer a swing state.
    lean = fundamentals.presidential_lean(IA["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_iowa_registration_trend_uses_the_two_most_recent_snapshots():
    # Both the Oct 2024 and Jul 2026 snapshots postdate Iowa's 2024
    # active/inactive-status law change, so they're apples-to-apples even
    # though earlier snapshots in the list aren't comparable to them.
    adjustment = fundamentals.registration_trend_adjustment(IA["registration_snapshots"])
    assert adjustment != 0.0


def test_more_recent_elections_are_weighted_more_heavily():
    # Synthetic, deliberately monotonic series so "closer to the most recent
    # result" is an unambiguous property of the weighting itself — real PA/OH
    # data isn't monotonic (e.g. PA's 2018 governor race was a bigger
    # Democratic win than either 2014 or 2022 around it), so testing this
    # mechanism against real data can fail for reasons that have nothing to
    # do with the recency-weighting logic being wrong.
    elections = [
        {"year": 2014, "dem_share": 40.0},
        {"year": 2018, "dem_share": 45.0},
        {"year": 2022, "dem_share": 60.0},
    ]
    short_half_life_lean = fundamentals._recency_weighted_dem_margin(
        elections, date(2026, 7, 10), half_life_years=4.0
    )
    long_half_life_lean = fundamentals._recency_weighted_dem_margin(
        elections, date(2026, 7, 10), half_life_years=40.0
    )
    most_recent_margin = 2 * elections[-1]["dem_share"] - 100
    assert abs(short_half_life_lean - most_recent_margin) < abs(
        long_half_life_lean - most_recent_margin
    )


def test_combined_historical_lean_blends_all_three_series_by_configured_weight():
    as_of = date(2026, 7, 10)
    gub = fundamentals.gubernatorial_lean(PA["gubernatorial_elections"], as_of)
    sen = fundamentals.senate_lean(PA["senate_elections"], as_of)
    pres = fundamentals.presidential_lean(PA["presidential_elections"], as_of)
    combined = fundamentals.combined_historical_lean(
        PA["gubernatorial_elections"], PA["senate_elections"], PA["presidential_elections"], as_of
    )
    w_gov = fundamentals.settings.gubernatorial_lean_weight
    w_sen = fundamentals.settings.senate_lean_weight
    w_pres = 1 - w_gov - w_sen

    assert abs(combined - (w_gov * gub + w_sen * sen + w_pres * pres)) < 1e-9
    # blended value must land within the range of the three component leans
    assert min(gub, sen, pres) <= combined <= max(gub, sen, pres)


def test_historical_lean_weights_sum_to_one():
    w_gov, w_sen, w_pres = fundamentals._historical_lean_weights()
    assert abs((w_gov + w_sen + w_pres) - 1.0) < 1e-9


def test_incumbency_adjustment_sign():
    assert fundamentals.incumbency_adjustment("Democratic") > 0
    assert fundamentals.incumbency_adjustment("Republican") < 0
    assert fundamentals.incumbency_adjustment(None) == 0


def test_registration_trend_adjustment_is_neutral_when_no_data():
    # Ohio doesn't register voters by party -> empty list -> neutral 0.
    assert fundamentals.registration_trend_adjustment(OH["registration_snapshots"]) == 0.0


def test_registration_trend_adjustment_uses_pa_data():
    adjustment = fundamentals.registration_trend_adjustment(PA["registration_snapshots"])
    assert adjustment != 0.0


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
        PA, "Democratic", "Democratic", approval_pct=37.0, president_party="Republican"
    )
    rep_share = fundamentals.fundamentals_vote_share(
        PA, "Republican", "Democratic", approval_pct=37.0, president_party="Republican"
    )
    assert abs((dem_share + rep_share) - 100) < 1e-9
    assert dem_share > rep_share


def test_ohio_fundamentals_favor_republican_candidate():
    rep_share = fundamentals.fundamentals_vote_share(
        OH, "Republican", None, approval_pct=37.0, president_party="Republican"
    )
    assert rep_share > 50


def test_poll_weight_reaches_ceiling_on_election_day():
    weight = fundamentals.poll_weight_for_election(
        fundamentals.ELECTION_DATE, as_of=fundamentals.ELECTION_DATE
    )
    assert weight == fundamentals.settings.poll_weight_ceiling


def test_poll_weight_approaches_floor_far_out():
    weight = fundamentals.poll_weight_for_election(
        fundamentals.ELECTION_DATE, as_of=date(2025, 1, 1)
    )  # >600 days out
    assert abs(weight - fundamentals.settings.poll_weight_floor) < 0.01


def test_poll_weight_decreases_monotonically_with_days_to_election():
    election_date = fundamentals.ELECTION_DATE
    close = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 10, 30))  # T=4
    mid = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 9, 1))  # T=63
    far = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 1, 1))  # T=306

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
    election_date = fundamentals.ELECTION_DATE
    two_weeks_out = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 10, 20))
    five_weeks_out = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 9, 26))
    four_months_out = fundamentals.poll_weight_for_election(election_date, as_of=date(2026, 7, 3))

    assert abs(two_weeks_out - 0.80) < 0.1
    assert abs(five_weeks_out - 0.60) < 0.1
    assert abs(four_months_out - 0.40) < 0.1
