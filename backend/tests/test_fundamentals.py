from datetime import date

from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.services import fundamentals

PA = RACE_FUNDAMENTALS["pa"]
OH = RACE_FUNDAMENTALS["oh"]
GA = RACE_FUNDAMENTALS["ga"]
ME = RACE_FUNDAMENTALS["me"]
IA = RACE_FUNDAMENTALS["ia"]
NY = RACE_FUNDAMENTALS["ny"]
SC = RACE_FUNDAMENTALS["sc"]
TX = RACE_FUNDAMENTALS["tx"]
FL = RACE_FUNDAMENTALS["fl"]
NV = RACE_FUNDAMENTALS["nv"]
IL = RACE_FUNDAMENTALS["il"]
OR_ = RACE_FUNDAMENTALS["or"]
MI = RACE_FUNDAMENTALS["mi"]
NE = RACE_FUNDAMENTALS["ne"]
KS = RACE_FUNDAMENTALS["ks"]
AZ = RACE_FUNDAMENTALS["az"]
NH = RACE_FUNDAMENTALS["nh"]
CO = RACE_FUNDAMENTALS["co"]
VT = RACE_FUNDAMENTALS["vt"]
MA = RACE_FUNDAMENTALS["ma"]
MD = RACE_FUNDAMENTALS["md"]
CA = RACE_FUNDAMENTALS["ca"]
NM = RACE_FUNDAMENTALS["nm"]
AL = RACE_FUNDAMENTALS["al"]
AR = RACE_FUNDAMENTALS["ar"]
WI = RACE_FUNDAMENTALS["wi"]
ID = RACE_FUNDAMENTALS["id"]


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


def test_new_york_gubernatorial_lean_favors_democratic():
    # Cuomo/Hochul have won all 3 of the last NY governor races comfortably,
    # each above 53% two-party share.
    lean = fundamentals.gubernatorial_lean(NY["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_new_york_senate_lean_favors_democratic():
    # Gillibrand and Schumer have both won their last races by 15+ points.
    lean = fundamentals.senate_lean(NY["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_new_york_presidential_lean_favors_democratic():
    # NY hasn't gone Republican since 1984, though 2024 saw its largest
    # rightward swing of any state.
    lean = fundamentals.presidential_lean(NY["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_new_york_registration_trend_uses_official_boe_snapshots():
    adjustment = fundamentals.registration_trend_adjustment(NY["registration_snapshots"])
    assert adjustment != 0.0


def test_south_carolina_gubernatorial_lean_favors_republican():
    # Haley/McMaster have won all 3 of the last SC governor races solidly.
    lean = fundamentals.gubernatorial_lean(SC["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_south_carolina_senate_lean_favors_republican():
    # Scott and Graham have both won their last races by double digits.
    lean = fundamentals.senate_lean(SC["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_south_carolina_presidential_lean_favors_republican():
    lean = fundamentals.presidential_lean(SC["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_south_carolina_has_no_registration_data():
    # South Carolina doesn't register voters by party (open primaries).
    assert fundamentals.registration_trend_adjustment(SC["registration_snapshots"]) == 0.0


def test_texas_gubernatorial_lean_favors_republican():
    # Abbott has won all 3 of the last TX governor races solidly.
    lean = fundamentals.gubernatorial_lean(TX["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_texas_senate_lean_favors_republican():
    # Cruz and Cornyn have both won their last races, Cruz's 2018 race
    # notwithstanding being unusually close.
    lean = fundamentals.senate_lean(TX["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_texas_presidential_lean_favors_republican():
    lean = fundamentals.presidential_lean(TX["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_texas_has_no_registration_data():
    # Texas doesn't register voters by party (open primaries).
    assert fundamentals.registration_trend_adjustment(TX["registration_snapshots"]) == 0.0


def test_florida_gubernatorial_lean_is_close_to_even():
    # FL's last 3 governor races: 2014/2018 were near-toss-ups, 2022 was a
    # DeSantis landslide -- net lean should tilt Republican but not extreme.
    lean = fundamentals.gubernatorial_lean(FL["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_florida_senate_lean_favors_republican():
    lean = fundamentals.senate_lean(FL["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < 0


def test_florida_presidential_lean_favors_republican():
    # Florida is no longer a swing state at the presidential level.
    lean = fundamentals.presidential_lean(FL["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -3


def test_florida_registration_trend_shows_the_republican_realignment():
    # FL flipped from a Dem to a widening Republican registration edge.
    adjustment = fundamentals.registration_trend_adjustment(FL["registration_snapshots"])
    assert adjustment < 0


def test_nevada_gubernatorial_lean_is_close_to_even():
    # NV's last 3 governor races: a 2014 GOP landslide, then two close
    # races each decided within a few points -- net lean should be mild.
    lean = fundamentals.gubernatorial_lean(NV["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert -15 < lean < 5


def test_nevada_senate_lean_favors_democratic():
    # Cortez Masto and Rosen have both won their last races, each narrowly.
    lean = fundamentals.senate_lean(NV["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_nevada_presidential_lean_is_close_to_even():
    # NV flipped to Trump in 2024 after backing Democrats in 2016/2020 --
    # a genuine swing state.
    lean = fundamentals.presidential_lean(NV["presidential_elections"], as_of=date(2026, 7, 10))
    assert -5 < lean < 5


def test_nevada_registration_trend_shows_a_narrowing_democratic_edge():
    # NV's Dem registration lead shrank from +50K (2022) to +502 (2026).
    adjustment = fundamentals.registration_trend_adjustment(NV["registration_snapshots"])
    assert adjustment < 0


def test_illinois_gubernatorial_lean_favors_democratic():
    # Pritzker has won the last 2 of 3 IL governor races comfortably.
    lean = fundamentals.gubernatorial_lean(IL["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_illinois_senate_lean_favors_democratic():
    # Duckworth and Durbin have both won their last races comfortably.
    lean = fundamentals.senate_lean(IL["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_illinois_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(IL["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_illinois_has_no_registration_data():
    # Illinois doesn't register voters by party.
    assert fundamentals.registration_trend_adjustment(IL["registration_snapshots"]) == 0.0


def test_oregon_gubernatorial_lean_favors_democratic():
    # Kitzhaber/Brown/Kotek have won all 3 of the last OR governor races.
    lean = fundamentals.gubernatorial_lean(OR_["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_oregon_senate_lean_favors_democratic():
    # Wyden and Merkley have both won their last races comfortably.
    lean = fundamentals.senate_lean(OR_["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_oregon_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(OR_["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_oregon_registration_trend_shows_a_narrowing_democratic_edge():
    # OR's Dem registration lead has shrunk every cycle since 2020 as
    # automatic voter registration grows the nonaffiliated bloc.
    adjustment = fundamentals.registration_trend_adjustment(OR_["registration_snapshots"])
    assert adjustment < 0


def test_michigan_gubernatorial_lean_favors_democratic():
    # Whitmer won both of the last 2 races comfortably; only 2014 (Snyder)
    # was Republican, and it's the most-decayed of the 3.
    lean = fundamentals.gubernatorial_lean(MI["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_michigan_senate_lean_favors_democratic():
    lean = fundamentals.senate_lean(MI["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_michigan_presidential_lean_is_close_to_even():
    # MI has split its last 3 presidential results (Trump/Biden/Trump), each
    # within about a point or two -- a genuine swing state.
    lean = fundamentals.presidential_lean(MI["presidential_elections"], as_of=date(2026, 7, 10))
    assert -5 < lean < 5


def test_michigan_has_no_registration_data():
    # Michigan doesn't register voters by party.
    assert fundamentals.registration_trend_adjustment(MI["registration_snapshots"]) == 0.0


def test_nebraska_gubernatorial_lean_favors_republican():
    # Ricketts/Pillen have won all 3 of the last NE governor races, each by
    # double digits in two-party terms.
    lean = fundamentals.gubernatorial_lean(NE["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_nebraska_senate_lean_favors_republican():
    # Fischer, Sasse, and Ricketts have all won their last races, each by a
    # comfortable double-digit two-party margin.
    lean = fundamentals.senate_lean(NE["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_nebraska_presidential_lean_favors_republican():
    # Nebraska hasn't gone Democratic statewide since 1964 -- solidly
    # Republican at the presidential level.
    lean = fundamentals.presidential_lean(NE["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -10


def test_nebraska_registration_trend_shows_a_widening_republican_edge():
    # NE's registered-Republican advantage grew steadily from the Sept. 2022
    # snapshot through the most recent (May 2026) one.
    adjustment = fundamentals.registration_trend_adjustment(NE["registration_snapshots"])
    assert adjustment < 0


def test_kansas_gubernatorial_lean_is_nearly_even_but_slightly_democratic():
    # Kansas governor races have been genuinely close for over a decade
    # (48-53% two-party) despite the state being solidly Republican
    # federally -- Kelly's two wins keep the lean barely positive.
    lean = fundamentals.gubernatorial_lean(KS["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert 0 < lean < 5


def test_kansas_senate_lean_favors_republican():
    # Both KS Senate seats have been comfortably Republican-held across the
    # last 3 elections used (Moran 2016, Marshall 2020, Moran 2022).
    lean = fundamentals.senate_lean(KS["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -10


def test_kansas_presidential_lean_favors_republican():
    # Kansas hasn't gone Democratic statewide since 1964.
    lean = fundamentals.presidential_lean(KS["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -10


def test_kansas_registration_trend_shows_a_widening_republican_edge():
    adjustment = fundamentals.registration_trend_adjustment(KS["registration_snapshots"])
    assert adjustment < 0


def test_arizona_gubernatorial_lean_favors_republican_on_a_recency_weighted_basis():
    # 2014 and 2018 were both real R wins (Ducey); 2022 (Hobbs) was a real
    # but narrow D win. The recency-weighted lean still nets slightly R.
    lean = fundamentals.gubernatorial_lean(AZ["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert -15 < lean < 0


def test_arizona_senate_lean_favors_democratic():
    # AZ's last 3 Senate results across both seats (Kelly x2, Gallego) were
    # all real, if narrow, Democratic wins.
    lean = fundamentals.senate_lean(AZ["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_arizona_presidential_lean_is_close_to_even():
    # AZ has been a genuine presidential swing state this decade (Biden won
    # it in 2020, Trump won it in 2016 and 2024, all by single digits).
    lean = fundamentals.presidential_lean(AZ["presidential_elections"], as_of=date(2026, 7, 10))
    assert -10 < lean < 10


def test_arizona_registration_trend_is_small_and_non_monotonic():
    # AZ's registered-independent bloc is huge and growing, and the raw
    # D-vs-R gap isn't a clean trend over these 3 snapshots -- the
    # adjustment should stay small in magnitude either way.
    adjustment = fundamentals.registration_trend_adjustment(AZ["registration_snapshots"])
    assert abs(adjustment) < 2


def test_new_hampshire_gubernatorial_lean_favors_republican():
    # 2020 (Sununu's COVID-era landslide over Feltes) still weighs heavily
    # even after recency weighting, despite 2022 and 2024 both being much
    # closer real Republican wins.
    lean = fundamentals.gubernatorial_lean(NH["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -5


def test_new_hampshire_senate_lean_favors_democratic():
    # All 3 of NH's last Senate results across both seats (Hassan x2,
    # Shaheen) were real Democratic wins, one a near-tie and one a landslide.
    lean = fundamentals.senate_lean(NH["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_new_hampshire_presidential_lean_favors_democratic():
    # NH has gone Democratic in all 3 of the last presidential elections,
    # consistent with its status as a light-blue swing state.
    lean = fundamentals.presidential_lean(NH["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_new_hampshire_registration_trend_is_stable_after_the_republican_flip():
    # Democrats held a raw registration lead in 2020/2022; Republicans
    # flipped ahead by the 2024 snapshot. But the trend adjustment only
    # looks at the trailing two snapshots (Aug 2025 -> May 2026), and the R
    # lead was essentially flat over that span, so it should stay small.
    adjustment = fundamentals.registration_trend_adjustment(NH["registration_snapshots"])
    assert abs(adjustment) < 2


def test_colorado_gubernatorial_lean_favors_democratic():
    # All 3 of CO's last governor races were real Democratic wins, including
    # a genuine landslide in 2022 (Polis d. Ganahl by ~20 raw points).
    lean = fundamentals.gubernatorial_lean(CO["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_colorado_senate_lean_favors_democratic():
    # All 3 of CO's last Senate results across both seats (Bennet x2,
    # Hickenlooper's 2020 flip) were real Democratic wins.
    lean = fundamentals.senate_lean(CO["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_colorado_presidential_lean_favors_democratic():
    # CO has gone Democratic by a growing then slightly narrowing double
    # digit two-party margin in all 3 of the last presidential elections.
    lean = fundamentals.presidential_lean(CO["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 5


def test_colorado_registration_trend_is_small():
    # CO's Democratic raw registration lead has been fairly stable (~87K to
    # ~104K) across these snapshots even as unaffiliated voters have grown
    # to a majority of the electorate -- the trailing two-point trend
    # adjustment should stay small.
    adjustment = fundamentals.registration_trend_adjustment(CO["registration_snapshots"])
    assert abs(adjustment) < 2


def test_vermont_gubernatorial_lean_favors_republican():
    # Phil Scott (R) has won all 3 of the last governor races by landslide
    # two-party margins despite VT being heavily Democratic otherwise.
    lean = fundamentals.gubernatorial_lean(VT["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -30


def test_vermont_senate_lean_favors_democratic():
    # Sanders (I, caucuses D) and Welch have all won their last races by
    # landslide two-party margins.
    lean = fundamentals.senate_lean(VT["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 20


def test_vermont_presidential_lean_favors_democratic():
    # VT is one of the most reliably Democratic states presidentially.
    lean = fundamentals.presidential_lean(VT["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 20


def test_vermont_has_no_registration_data():
    # VT doesn't register voters by party (same as GA/OH).
    assert fundamentals.registration_trend_adjustment(VT["registration_snapshots"]) == 0.0


def test_massachusetts_gubernatorial_lean_is_close_to_even_despite_being_deep_blue():
    # MA is famous for electing popular moderate Republican governors
    # (Baker won 2014 open-seat and 2018 landslide reelection) even though
    # the state is otherwise deep blue -- Healey's 2022 landslide isn't
    # enough on its own to pull the recency-weighted lean solidly positive.
    lean = fundamentals.gubernatorial_lean(MA["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert -10 < lean < 10


def test_massachusetts_senate_lean_favors_democratic():
    lean = fundamentals.senate_lean(MA["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_massachusetts_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(MA["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_massachusetts_registration_trend_is_small():
    adjustment = fundamentals.registration_trend_adjustment(MA["registration_snapshots"])
    assert abs(adjustment) < 2


def test_maryland_gubernatorial_lean_favors_democratic():
    lean = fundamentals.gubernatorial_lean(MD["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_maryland_senate_lean_favors_democratic():
    lean = fundamentals.senate_lean(MD["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_maryland_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(MD["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_maryland_registration_trend_is_small():
    # MD's Democratic raw registration lead has been fairly stable (~1.19M
    # to ~1.20M) across these recent snapshots.
    adjustment = fundamentals.registration_trend_adjustment(MD["registration_snapshots"])
    assert abs(adjustment) < 2


def test_california_gubernatorial_lean_favors_democratic():
    lean = fundamentals.gubernatorial_lean(CA["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_california_senate_lean_favors_democratic():
    lean = fundamentals.senate_lean(CA["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 10


def test_california_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(CA["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 15


def test_california_registration_trend_is_small():
    # CA's Democratic raw registration lead is enormous (~4.5-5M), and the
    # trend adjustment is a damped *percent change*, not a raw-count read,
    # so it should stay small regardless of the huge absolute lead.
    adjustment = fundamentals.registration_trend_adjustment(CA["registration_snapshots"])
    assert abs(adjustment) < 2


def test_new_mexico_gubernatorial_lean_favors_democratic():
    lean = fundamentals.gubernatorial_lean(NM["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_new_mexico_senate_lean_favors_democratic():
    lean = fundamentals.senate_lean(NM["senate_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_new_mexico_presidential_lean_favors_democratic():
    lean = fundamentals.presidential_lean(NM["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean > 0


def test_new_mexico_registration_trend_is_small():
    # NM's Democratic raw registration lead has been fairly stable
    # (~130K-131K) across these snapshots.
    adjustment = fundamentals.registration_trend_adjustment(NM["registration_snapshots"])
    assert abs(adjustment) < 2


def test_alabama_gubernatorial_lean_favors_republican():
    lean = fundamentals.gubernatorial_lean(AL["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_alabama_senate_lean_favors_republican():
    lean = fundamentals.senate_lean(AL["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_alabama_presidential_lean_favors_republican():
    lean = fundamentals.presidential_lean(AL["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_alabama_has_no_registration_data():
    # Alabama doesn't register voters by party.
    assert fundamentals.registration_trend_adjustment(AL["registration_snapshots"]) == 0.0


def test_arkansas_gubernatorial_lean_favors_republican():
    lean = fundamentals.gubernatorial_lean(AR["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_arkansas_senate_lean_favors_republican():
    lean = fundamentals.senate_lean(AR["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_arkansas_presidential_lean_favors_republican():
    lean = fundamentals.presidential_lean(AR["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_arkansas_has_no_registration_data():
    # Arkansas doesn't register voters by party.
    assert fundamentals.registration_trend_adjustment(AR["registration_snapshots"]) == 0.0


def test_wisconsin_gubernatorial_lean_is_a_genuine_toss_up():
    # WI is one of the closest-divided swing states -- every lean here
    # should be small in magnitude, not lopsided either direction.
    lean = fundamentals.gubernatorial_lean(WI["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert abs(lean) < 5


def test_wisconsin_senate_lean_is_a_genuine_toss_up():
    lean = fundamentals.senate_lean(WI["senate_elections"], as_of=date(2026, 7, 10))
    assert abs(lean) < 5


def test_wisconsin_presidential_lean_is_a_genuine_toss_up():
    lean = fundamentals.presidential_lean(WI["presidential_elections"], as_of=date(2026, 7, 10))
    assert abs(lean) < 5


def test_wisconsin_has_no_registration_data():
    # Wisconsin doesn't register voters by party.
    assert fundamentals.registration_trend_adjustment(WI["registration_snapshots"]) == 0.0


def test_idaho_gubernatorial_lean_favors_republican():
    lean = fundamentals.gubernatorial_lean(ID["gubernatorial_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_idaho_senate_lean_favors_republican():
    lean = fundamentals.senate_lean(ID["senate_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_idaho_presidential_lean_favors_republican():
    lean = fundamentals.presidential_lean(ID["presidential_elections"], as_of=date(2026, 7, 10))
    assert lean < -15


def test_idaho_registration_trend_is_a_noop_with_a_single_snapshot():
    # Only one snapshot on file -- the trend adjustment needs two to compute
    # a trailing change, so it's a documented no-op (0.0), not an error.
    assert fundamentals.registration_trend_adjustment(ID["registration_snapshots"]) == 0.0


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
