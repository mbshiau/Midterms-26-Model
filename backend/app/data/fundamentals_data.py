"""Real historical inputs for the fundamentals model (see app.services.fundamentals),
keyed by state_code. Only PRESIDENT is national (shared across every race).

Sources:
- Historical gubernatorial/Senate results: Wikipedia/Ballotpedia/uselectionatlas
  results pages for each cited year. `dem_share` is the Democratic
  candidate's two-party vote share, i.e. renormalized to exclude
  third-party/write-in votes.
- Historical presidential results: Wikipedia's "United States presidential
  elections in <state>" and per-year election articles. Same two-party
  renormalization.
- Registration snapshots: state-specific voter-file statistics where the
  state actually tracks party registration (PA does; Ohio doesn't — Ohio
  voters aren't registered by party, so its list is empty and that
  fundamentals input is a no-op for Ohio's forecast).
- Presidential approval: aggregated national approval polling as of
  2026-07-10 (Silver Bulletin / FiftyPlusOne approval trackers), Trump
  (R), 2nd term.
"""

from datetime import date

ELECTION_DATE = date(2026, 11, 3)

RACE_FUNDAMENTALS = {
    "pa": {
        # year, Democratic candidate's two-party vote share, which party
        # (if any) held the seat as the incumbent running for reelection.
        # Last 3 cycles only (trimmed from 6, same rationale as
        # presidential below): 2002-2010 are judged too dated.
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 54.90, "incumbent_party": "R"},  # Wolf d. Corbett (inc)
            {"year": 2018, "dem_share": 58.68, "incumbent_party": "D"},  # Wolf (inc) d. Wagner
            {"year": 2022, "dem_share": 56.24, "incumbent_party": None},  # Shapiro d. Mastriano, open seat
        ],
        # Last 3 PA Senate elections (either seat/class — PA's two seats are
        # staggered, so "last 3" mixes both). Senate races are the other
        # genuinely statewide race besides governor and president, so this
        # adds a third independent read on the state's partisan lean.
        "senate_elections": [
            {"year": 2018, "dem_share": 56.70},  # Casey (D, inc) d. Barletta
            {"year": 2022, "dem_share": 52.51},  # Fetterman (D) d. Oz
            {"year": 2024, "dem_share": 49.78},  # McCormick (R) d. Casey (D, inc)
        ],
        # Last 3 presidential results, same two-party-share convention.
        # Trimmed from 6 to 3 cycles deliberately: the electorate has
        # shifted enough since the Obama era (deindustrialization backlash,
        # realignment of white working-class and college-educated voters)
        # that 2004-2012 are judged too dated to usefully describe the
        # state's current partisan lean.
        "presidential_elections": [
            {"year": 2016, "dem_share": 49.62},  # Trump d. Clinton (PA flipped R)
            {"year": 2020, "dem_share": 50.59},  # Biden d. Trump
            {"year": 2024, "dem_share": 49.14},  # Trump d. Harris
        ],
        # Statewide registered-voter count, Democratic minus Republican.
        "registration_snapshots": [
            {"date": "2016-12-31", "dem_lead": 916_000},
            {"date": "2020-12-31", "dem_lead": 685_818},
            {"date": "2022-12-31", "dem_lead": 549_568},
            {"date": "2024-11-30", "dem_lead": 286_283},
            {"date": "2025-07-31", "dem_lead": 59_135},
            {"date": "2025-10-31", "dem_lead": 170_608},
            {"date": "2026-05-31", "dem_lead": 188_381},
        ],
    },
    "oh": {
        # Last 3 cycles only (trimmed from 6): 2002-2010 dropped.
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 34.02, "incumbent_party": "R"},  # Kasich (inc) d. FitzGerald
            {"year": 2018, "dem_share": 48.09, "incumbent_party": None},  # DeWine d. Cordray, open seat
            {"year": 2022, "dem_share": 37.20, "incumbent_party": "R"},  # DeWine (inc) d. Whaley
        ],
        # Last 3 Ohio Senate elections (either seat/class).
        "senate_elections": [
            {"year": 2018, "dem_share": 53.40},  # Brown (D, inc) d. Renacci
            {"year": 2022, "dem_share": 47.00},  # Vance (R) d. Ryan
            {"year": 2024, "dem_share": 48.03},  # Moreno (R) d. Brown (D, inc)
        ],
        # Last 3 presidential results. Ohio has moved decisively away from
        # swing-state status since 2016 (unlike PA), so this pulls the
        # combined historical lean solidly Republican rather than trimming
        # it toward zero the way PA's does.
        "presidential_elections": [
            {"year": 2016, "dem_share": 45.83},  # Trump d. Clinton
            {"year": 2020, "dem_share": 45.92},  # Trump d. Biden
            {"year": 2024, "dem_share": 44.29},  # Trump d. Harris
        ],
        # Ohio does not register voters by party, so there's no D-minus-R
        # registration figure to track — this input is simply absent, and
        # the fundamentals model treats an empty list as a neutral 0 rather
        # than fabricating a number.
        "registration_snapshots": [],
    },
    "ga": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 45.92, "incumbent_party": "R"},  # Deal (inc) d. Carter
            {"year": 2018, "dem_share": 49.29, "incumbent_party": None},  # Kemp d. Abrams, open seat
            {"year": 2022, "dem_share": 46.23, "incumbent_party": "R"},  # Kemp (inc) d. Abrams
        ],
        # Georgia's two Senate seats don't stagger evenly — its last 3
        # decisive results are the Jan. 2021 double-runoff (both seats) plus
        # the Dec. 2022 runoff. `year` uses the election-cycle year (not the
        # runoff month) for consistency with how these races are commonly
        # referenced.
        "senate_elections": [
            {"year": 2020, "dem_share": 50.40},  # Ossoff (D) d. Perdue, Jan. 2021 runoff
            {"year": 2020, "dem_share": 50.80},  # Warnock (D) d. Loeffler, special, Jan. 2021 runoff
            {"year": 2022, "dem_share": 51.40},  # Warnock (D, inc) d. Walker, Dec. 2022 runoff
        ],
        # Last 3 presidential results. Georgia has been the closest kind of
        # swing state this decade — Biden's 2020 win by ~12,000 votes was the
        # tightest state margin in the country that year.
        "presidential_elections": [
            {"year": 2016, "dem_share": 47.35},  # Trump d. Clinton
            {"year": 2020, "dem_share": 50.12},  # Biden d. Trump
            {"year": 2024, "dem_share": 49.00},  # Trump d. Harris
        ],
        # Georgia doesn't register voters by party (open primaries; party is
        # only observable from primary participation, not registration), so
        # there's no D-minus-R figure to track here either.
        "registration_snapshots": [],
    },
    "me": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 47.4, "incumbent_party": "R"},  # LePage (inc) d. Michaud; Cutler (I) 8.4%
            {"year": 2018, "dem_share": 54.1, "incumbent_party": None},  # Mills d. Moody, open seat (LePage term-limited)
            {"year": 2022, "dem_share": 56.7, "incumbent_party": "D"},  # Mills (inc) d. LePage
        ],
        # Maine's last 3 Senate races (either seat/class). Both 2018 and 2024
        # were won by Angus King, an independent who caucuses with Senate
        # Democrats and who vastly outperformed the actual Democratic
        # nominee (a token candidate polling ~10% in each race). Using the
        # literal D-nominee share would understate the state's real
        # Democratic-leaning disposition in these races, so King's share is
        # bucketed with the Democratic-aligned nominee's, consistent with
        # how he actually competes for the seat.
        "senate_elections": [
            {"year": 2018, "dem_share": 64.8},  # King (I, caucuses D) + Ringelstein (D) vs. Brakey (R)
            {"year": 2020, "dem_share": 45.4},  # Collins (R) d. Gideon (D)
            {"year": 2024, "dem_share": 64.7},  # King (I, caucuses D) + Costello (D) vs. Kouzounas (R)
        ],
        # Last 3 presidential results, statewide two-party share (Maine
        # splits 2 of its 4 electoral votes by congressional district, but
        # this fundamentals input uses the statewide popular vote, same
        # convention as every other state here).
        "presidential_elections": [
            {"year": 2016, "dem_share": 51.6},  # Clinton d. Trump
            {"year": 2020, "dem_share": 54.7},  # Biden d. Trump
            {"year": 2024, "dem_share": 53.5},  # Harris d. Trump
        ],
        # Maine does register voters by party (unlike Ohio/Georgia), but
        # only one reliably primary-sourced statewide snapshot could be
        # located (Maine SOS, 2025-02-06) -- not enough for the 2-point
        # trend this input needs, so it's left empty (neutral 0) rather than
        # pairing a verified snapshot with an unverified secondary-sourced
        # historical figure.
        "registration_snapshots": [],
    },
    "ia": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 38.72, "incumbent_party": "R"},  # Branstad (inc) d. Hatch
            {"year": 2018, "dem_share": 48.60, "incumbent_party": "R"},  # Reynolds (inc, elevated 2017) d. Hubbell
            {"year": 2022, "dem_share": 40.51, "incumbent_party": "R"},  # Reynolds (inc) d. DeJear
        ],
        # Last 3 Iowa Senate elections (mixes both classes: Grassley's
        # Class II and Ernst's Class III).
        "senate_elections": [
            {"year": 2016, "dem_share": 37.24},  # Grassley (R, inc) d. Judge
            {"year": 2020, "dem_share": 46.60},  # Ernst (R, inc) d. Greenfield
            {"year": 2022, "dem_share": 43.90},  # Grassley (R, inc) d. Franken
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 44.94},  # Trump d. Clinton
            {"year": 2020, "dem_share": 45.82},  # Trump d. Biden
            {"year": 2024, "dem_share": 43.28},  # Trump d. Harris
        ],
        # Iowa SoS publishes official active-voter registration by party.
        # Note a 2024 state-law change retroactively tightened the
        # definition of "inactive" (a single missed even-year general
        # election now moves a voter to inactive), which is why active
        # totals drop sharply between the Oct 2022 and Oct 2024 snapshots --
        # that's a methodology break, not real attrition, so it's included
        # for the historical record but registration_trend_adjustment only
        # ever compares the last two snapshots, which are both post-change
        # and therefore apples-to-apples.
        "registration_snapshots": [
            {"date": "2020-10-01", "dem_lead": -13_085},
            {"date": "2022-10-03", "dem_lead": -88_024},
            {"date": "2024-10-01", "dem_lead": -166_858},
            {"date": "2026-07-02", "dem_lead": -183_912},
        ],
    },
    "ny": {
        # NY has fusion voting: candidates often run on both a major party
        # line and a minor party line (e.g. Working Families, Conservative).
        # dem_share/rep_share below combine a candidate's major-line and
        # fusion-line votes (same candidate, not a spoiler), matching how
        # Wikipedia's own results tables report "combined" totals.
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 57.39, "incumbent_party": "D"},  # Cuomo (inc) d. Astorino
            {"year": 2018, "dem_share": 62.23, "incumbent_party": "D"},  # Cuomo (inc) d. Molinaro
            {"year": 2022, "dem_share": 53.20, "incumbent_party": "D"},  # Hochul (inc) d. Zeldin
        ],
        # Last 3 NY Senate elections (mixes Gillibrand's Class 1 and
        # Schumer's Class 3 seats), combined-line totals.
        "senate_elections": [
            {"year": 2018, "dem_share": 67.00},  # Gillibrand (inc) d. Farley
            {"year": 2022, "dem_share": 57.04},  # Schumer (inc) d. Pinion
            {"year": 2024, "dem_share": 59.21},  # Gillibrand (inc) d. Sapraicone
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 61.78},  # Clinton d. Trump
            {"year": 2020, "dem_share": 61.73},  # Biden d. Trump
            {"year": 2024, "dem_share": 56.35},  # Harris d. Trump -- NY's largest R swing of any state in 2024
        ],
        # NYS Board of Elections publishes official statewide enrollment by
        # party (elections.ny.gov/enrollment-county). Direct access was
        # blocked by an anti-bot challenge; figures below are the same BOE
        # report retrieved via Internet Archive captures of the official
        # files, reconciled against their own Active+Inactive subtotals.
        # dem_lead = statewide Democratic minus Republican registration.
        "registration_snapshots": [
            {"date": "2020-02-21", "dem_lead": 3_720_174},
            {"date": "2022-02-21", "dem_lead": 3_623_202},
            {"date": "2022-11-01", "dem_lead": 3_615_902},
            {"date": "2024-02-27", "dem_lead": 3_500_925},
            {"date": "2026-02-20", "dem_lead": 3_450_766},
        ],
    },
    "sc": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 42.56, "incumbent_party": "R"},  # Haley (inc) d. Sheheen
            {"year": 2018, "dem_share": 46.00, "incumbent_party": "R"},  # McMaster (inc) d. Smith
            {"year": 2022, "dem_share": 41.20, "incumbent_party": "R"},  # McMaster (inc) d. Cunningham
        ],
        # Last 3 SC Senate elections (mixes Scott's Class II and Graham's
        # Class III seats; Graham's 2026 seat hasn't been up for election
        # yet as of this writing).
        "senate_elections": [
            {"year": 2016, "dem_share": 37.90},  # Scott (inc) d. Dixon
            {"year": 2020, "dem_share": 44.86},  # Graham (inc) d. Harrison
            {"year": 2022, "dem_share": 37.05},  # Scott (inc) d. Matthews
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 42.6},  # Trump d. Clinton
            {"year": 2020, "dem_share": 44.06},  # Trump d. Biden
            {"year": 2024, "dem_share": 40.92},  # Trump d. Harris
        ],
        # South Carolina doesn't register voters by party (open primaries;
        # a 2025 bill to start capturing party affiliation at registration
        # hasn't become law) -- no D-minus-R figure exists to track, same
        # as Ohio/Georgia.
        "registration_snapshots": [],
    },
    "tx": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 39.62, "incumbent_party": None},  # Abbott d. Davis, open seat (Perry not running)
            {"year": 2018, "dem_share": 43.23, "incumbent_party": "R"},  # Abbott (inc) d. Valdez
            {"year": 2022, "dem_share": 44.48, "incumbent_party": "R"},  # Abbott (inc) d. O'Rourke
        ],
        # Last 3 TX Senate elections (mixes Cruz's Class 1 and Cornyn's
        # Class 2 seats; Cornyn's 2026 seat is up concurrently but not yet
        # decided as of this writing, so it isn't one of the "last 3").
        "senate_elections": [
            {"year": 2018, "dem_share": 48.71},  # Cruz (inc) d. O'Rourke
            {"year": 2020, "dem_share": 45.05},  # Cornyn (inc) d. Hegar
            {"year": 2024, "dem_share": 45.65},  # Cruz (inc) d. Allred
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 45.29},  # Trump d. Clinton
            {"year": 2020, "dem_share": 47.17},  # Trump d. Biden
            {"year": 2024, "dem_share": 43.06},  # Trump d. Harris
        ],
        # Texas doesn't register voters by party (open primaries; a voter's
        # primary choice each cycle isn't a permanent registration record),
        # confirmed directly via the Texas Secretary of State.
        "registration_snapshots": [],
    },
    "fl": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 49.4, "incumbent_party": "R"},  # Scott (inc) d. Crist
            {"year": 2018, "dem_share": 49.8, "incumbent_party": None},  # DeSantis d. Gillum, open seat (Scott ran for Senate)
            {"year": 2022, "dem_share": 40.2, "incumbent_party": "R"},  # DeSantis (inc) d. Crist
        ],
        # Last 3 FL Senate elections (mixes Rubio's Class III seat and the
        # Class I seat Rick Scott won in 2018 and held in 2024).
        "senate_elections": [
            {"year": 2018, "dem_share": 49.9},  # Scott (R) d. Nelson (inc)
            {"year": 2022, "dem_share": 41.7},  # Rubio (R, inc) d. Demings
            {"year": 2024, "dem_share": 43.5},  # Scott (R, inc) d. Mucarsel-Powell
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 49.4},  # Trump d. Clinton
            {"year": 2020, "dem_share": 48.4},  # Trump d. Biden
            {"year": 2024, "dem_share": 44.6},  # Trump d. Harris
        ],
        # Florida Division of Elections publishes official statewide
        # registration by party. Registration flipped from a Democratic to
        # a widening Republican advantage over this span -- a real,
        # dramatic realignment, not a data artifact.
        "registration_snapshots": [
            {"date": "2020-05-31", "dem_lead": 97_215},
            {"date": "2022-05-31", "dem_lead": -383_954},
            {"date": "2024-05-31", "dem_lead": -1_156_082},
            {"date": "2026-05-31", "dem_lead": -1_514_893},
        ],
    },
}

PRESIDENT = {
    "name": "Donald Trump",
    "party": "Republican",
    "approval_pct": 37.0,
    "as_of": "2026-07-10",
}
