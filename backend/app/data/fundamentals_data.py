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
        # 2014 (Kasich d. FitzGerald, D 34.02%) was discarded as an outlier
        # -- FitzGerald's campaign collapsed amid personal scandals
        # unrelated to Ohio's partisan lean, making that result a poor read
        # on the state's actual gubernatorial disposition. Left at 2
        # elections rather than backfilling further back, per instruction.
        "gubernatorial_elections": [
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
        # Rob Sand (D) is a genuine crossover-appeal overperformer (won
        # statewide re-election as auditor in a state Trump carried by
        # double digits) -- per explicit direction, historical lean is
        # damped to just 40% of the fundamentals total (incumbency +
        # registration + national environment make up the other 60%, see
        # fundamentals.fundamentals_breakdown), and real-time polling counts
        # for much more than the standard state's decay curve gives it.
        "model_overrides": {
            "historical_lean_share": 0.40,
            "poll_weight_floor": 0.55,
            "poll_weight_ceiling": 0.95,
        },
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
    "nv": {
        # 2014 (Sandoval d. Goodman, D 25.3%) was discarded as an outlier
        # -- Goodman's campaign was severely underfunded and never
        # competitive, making that ~45-point landslide a poor read on
        # Nevada's actual gubernatorial disposition (contrast the genuinely
        # close 2018/2022 races). Left at 2 elections rather than
        # backfilling further back, per instruction.
        "gubernatorial_elections": [
            {"year": 2018, "dem_share": 52.2, "incumbent_party": None},  # Sisolak d. Laxalt, open seat (Sandoval term-limited)
            {"year": 2022, "dem_share": 49.2, "incumbent_party": "D"},  # Lombardo (R) d. Sisolak (inc)
        ],
        # Last 3 NV Senate elections (mixes Rosen's Class I seat and Cortez
        # Masto's Class III seat).
        "senate_elections": [
            {"year": 2018, "dem_share": 52.6},  # Rosen d. Heller (inc)
            {"year": 2022, "dem_share": 50.4},  # Cortez Masto (inc) d. Laxalt
            {"year": 2024, "dem_share": 50.9},  # Rosen (inc) d. Brown
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 51.3},  # Clinton d. Trump
            {"year": 2020, "dem_share": 51.2},  # Biden d. Trump
            {"year": 2024, "dem_share": 48.4},  # Trump d. Harris -- first GOP win in NV since 2004
        ],
        # Nevada Secretary of State publishes official registration by
        # party. Only snapshots with a directly-stated absolute D/R count
        # are used (a Sept. 2021 figure was reported only as a percentage
        # of an approximate total, so it's excluded rather than back-
        # computing a fabricated-precision count from it). The real trend
        # here is dramatic: Nevada's Democratic registration edge narrowed
        # from +50K in 2022 to just +502 statewide as of July 2026.
        "registration_snapshots": [
            {"date": "2022-10-01", "dem_lead": 50_142},
            {"date": "2026-07-07", "dem_lead": 502},
        ],
    },
    "il": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 47.97, "incumbent_party": "D"},  # Rauner d. Quinn (inc)
            {"year": 2018, "dem_share": 58.42, "incumbent_party": "R"},  # Pritzker d. Rauner (inc)
            {"year": 2022, "dem_share": 56.45, "incumbent_party": "D"},  # Pritzker (inc) d. Bailey
        ],
        # Last 3 IL Senate elections (mixes Duckworth's Class 3 seat and
        # Durbin's Class 2 seat; no IL Senate race occurred in 2018 since
        # neither seat was up, so these span 2016/2020/2022).
        "senate_elections": [
            {"year": 2016, "dem_share": 57.98},  # Duckworth d. Kirk (inc)
            {"year": 2020, "dem_share": 58.56},  # Durbin (inc) d. Curran
            {"year": 2022, "dem_share": 57.78},  # Duckworth (inc) d. Salvi
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 59.02},  # Clinton d. Trump
            {"year": 2020, "dem_share": 58.65},  # Biden d. Trump
            {"year": 2024, "dem_share": 55.57},  # Harris d. Trump
        ],
        # Illinois doesn't register voters by party (a voter simply
        # requests a party's primary ballot each cycle, with no persistent
        # registration record), confirmed via NCSL-style classification.
        "registration_snapshots": [],
    },
    "or": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 53.06, "incumbent_party": "D"},  # Kitzhaber (inc) d. Richardson
            {"year": 2018, "dem_share": 53.71, "incumbent_party": "D"},  # Brown (inc) d. Buehler
            # 2022 was a genuine 3-way race: Kotek (D) 47.0%, Drazan (R)
            # 43.5%, Betsy Johnson (I) 8.6%. dem_share here is the two-party
            # share (D/(D+R) = 917,074/(917,074+850,347)), excluding
            # Johnson's independent vote -- same convention used for
            # Maine's Bennett and Georgia-style third-party candidates
            # elsewhere in this dataset, not a special case for Oregon.
            {"year": 2022, "dem_share": 51.89, "incumbent_party": None},  # Kotek d. Drazan, Johnson (I); open seat (Brown term-limited)
        ],
        # Last 3 OR Senate elections (mixes Wyden's Class III and
        # Merkley's Class II seats).
        "senate_elections": [
            {"year": 2016, "dem_share": 62.94},  # Wyden (inc) d. Callahan
            {"year": 2020, "dem_share": 59.16},  # Merkley (inc) d. Perkins
            {"year": 2022, "dem_share": 57.71},  # Wyden (inc) d. Perkins
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 56.16},  # Clinton d. Trump
            {"year": 2020, "dem_share": 58.30},  # Biden d. Trump
            {"year": 2024, "dem_share": 57.42},  # Harris d. Trump
        ],
        # Oregon Secretary of State publishes official registration by
        # party. Automatic voter registration (since 2016) has driven a
        # real, steady trend: nonaffiliated voters are now the largest
        # bloc, and the Democratic registration lead has been narrowing
        # every cycle since 2020.
        "registration_snapshots": [
            {"date": "2020-11-03", "dem_lead": 292_777},
            {"date": "2022-10-05", "dem_lead": 282_282},
            {"date": "2024-11-06", "dem_lead": 275_183},
            {"date": "2026-07-06", "dem_lead": 245_276},
        ],
    },
    "ne": {
        # Nebraska caps governors at 2 consecutive elected terms. Heineman
        # (R) was termed out in 2014 (open seat, Ricketts's first win);
        # Ricketts himself was termed out in 2022 after 2014/2018 (open
        # seat, Pillen's first win). Only the 2018 Ricketts reelection was
        # a true incumbent race.
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 40.70, "incumbent_party": None},  # Ricketts d. Hassebrook, Elworth (L) 3.5%; open seat (Heineman term-limited)
            {"year": 2018, "dem_share": 41.00, "incumbent_party": "R"},  # Ricketts (inc) d. Krist
            {"year": 2022, "dem_share": 37.79, "incumbent_party": None},  # Pillen d. Blood, Zimmerman (L) 3.9%; open seat (Ricketts term-limited)
        ],
        # NE's 2 Senate seats: Fischer's (Class I, up 2018/2024/2030) and the
        # seat Ben Sasse held (Class II, up 2020/2026), which Pete Ricketts
        # was appointed to in 2023 after Sasse resigned and then won outright
        # in a Nov. 2024 special election to serve the rest of that term.
        # "Last 3" here is 2018/2020/2024-special. The OTHER 2024 NE Senate
        # race on the same ballot -- Fischer (R, inc) d. Dan Osborn -- is
        # deliberately excluded: Osborn ran as a true independent who
        # explicitly declined the state Democratic Party's support (and
        # Democrats fielded no candidate at all), so unlike Maine's Angus
        # King there's no real "Democratic share" to extract from that race
        # without fabricating one.
        "senate_elections": [
            {"year": 2018, "dem_share": 40.10},  # Fischer (R, inc) d. Raybould
            # 2020: the Nebraska Democratic Party publicly withdrew support
            # from its own nominee, Chris Janicek, in June 2020 after a
            # sexting/racist-remarks scandal, then endorsed a write-in,
            # Preston Love Jr., in September as the de facto Democratic
            # candidate (Janicek couldn't be removed from the ballot under
            # NE law). dem_share here combines Janicek's ballot-line votes
            # with Love's write-in votes as the real Democratic-aligned
            # total, the same combining convention used for Maine's King.
            {"year": 2020, "dem_share": 32.86},  # Sasse (R, inc) d. Janicek (D)/Love (D write-in, combined)
            {"year": 2024, "dem_share": 37.42},  # Ricketts (R) d. Love, special election for the balance of Sasse's term
        ],
        # Statewide two-party popular vote (NE splits 2 of its 5 electoral
        # votes by congressional district -- notably NE-02/Omaha, which
        # Democrats have carried each of the last 3 cycles -- but this
        # input uses the statewide popular vote, same convention as Maine).
        "presidential_elections": [
            {"year": 2016, "dem_share": 36.45},  # Trump d. Clinton
            {"year": 2020, "dem_share": 40.22},  # Trump d. Biden
            {"year": 2024, "dem_share": 39.58},  # Trump d. Harris
        ],
        # Nebraska registers voters by party (unlike OH/GA/IL/TX/SC/MI).
        # Figures are statewide Grand Total rows from the NE Secretary of
        # State's monthly VR Statistics Count Report PDFs (sos.nebraska.gov),
        # dem_lead = Democratic minus Republican registration. The trend is
        # a real, steadily widening Republican registration edge.
        "registration_snapshots": [
            {"date": "2022-09-01", "dem_lead": -259_720},
            {"date": "2024-10-01", "dem_lead": -280_763},
            {"date": "2026-05-01", "dem_lead": -293_084},
        ],
    },
    "ks": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 48.08, "incumbent_party": "R"},  # Brownback (inc) d. Davis; Libertarian Umbehr 4.05%
            {"year": 2018, "dem_share": 52.76, "incumbent_party": None},  # Kelly d. Kobach, open seat (Brownback term-limited); real independent Greg Orman took 6.50% raw, so Kelly's actual plurality was only 48.01% -- not a landslide either way, kept in the window
            {"year": 2022, "dem_share": 51.14, "incumbent_party": "D"},  # Kelly (inc) d. Schmidt; independent Pyle 2.03%, Libertarian Cordell 1.10%
        ],
        # Kansas's 2 Senate seats don't stagger evenly -- last 3 elections
        # chronologically across both seats (same convention as FL/GA/NE):
        # Moran's 2016 win, Marshall's 2020 open-seat win (Roberts retired),
        # and Moran's 2022 reelection. Seat A's 2014 race (Roberts, R, inc.
        # d. independent Greg Orman) is excluded from this window on its own
        # merits -- Democratic nominee Chad Taylor withdrew and was removed
        # from the ballot by court order, leaving no Democrat on the ballot
        # at all that cycle -- but it wouldn't have made the "last 3" cut
        # regardless.
        "senate_elections": [
            {"year": 2016, "dem_share": 34.15},  # Moran (R, inc) d. Wiesner
            {"year": 2020, "dem_share": 43.98},  # Marshall d. Bollier, open seat (Roberts retired)
            {"year": 2022, "dem_share": 38.17},  # Moran (R, inc) d. Holland
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 38.89},  # Trump d. Clinton
            {"year": 2020, "dem_share": 42.51},  # Trump d. Biden
            {"year": 2024, "dem_share": 41.79},  # Trump d. Harris
        ],
        # KS SOS publishes monthly statewide party-registration totals.
        # dem_lead = Democratic minus Republican registration. No archived
        # 2020 snapshot could be found (SOS's monthly archive only goes back
        # to mid-2021), so Nov 2021 stands in as the earliest real snapshot.
        "registration_snapshots": [
            {"date": "2021-11-01", "dem_lead": -355_412},
            {"date": "2022-11-01", "dem_lead": -360_671},
            {"date": "2024-11-01", "dem_lead": -389_924},
            {"date": "2026-06-01", "dem_lead": -394_642},
        ],
    },
    "az": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 43.78, "incumbent_party": None},  # Ducey d. DuVal, open seat (Brewer term-limited)
            {"year": 2018, "dem_share": 42.77, "incumbent_party": "R"},  # Ducey (inc) d. Garcia, a real R-environment year (Sinema won her Senate race the same cycle -- a split-ticket data point, not an error)
            {"year": 2022, "dem_share": 50.33, "incumbent_party": None},  # Hobbs d. Lake, open seat (Ducey term-limited)
        ],
        # AZ's 2 Senate seats don't stagger evenly -- last 3 elections
        # chronologically across both seats (same convention as FL/GA/KS/NE).
        "senate_elections": [
            {"year": 2020, "dem_share": 51.18},  # Kelly d. McSally (appointed inc), special election
            {"year": 2022, "dem_share": 52.51},  # Kelly (inc) d. Masters
            {"year": 2024, "dem_share": 51.24},  # Gallego d. Lake, open seat (Sinema retired as an independent)
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 48.11},  # Trump d. Clinton
            {"year": 2020, "dem_share": 50.16},  # Biden d. Trump
            {"year": 2024, "dem_share": 47.22},  # Trump d. Harris
        ],
        # AZ SOS publishes statewide registration by party. AZ is unusual in
        # that registered independents ("no party preference") are a huge,
        # growing bloc -- often larger than either major party -- which is a
        # real structural feature of the electorate, not an anomaly. Only
        # the 3 most recent snapshots are used here: earlier (2020/2022)
        # figures found in secondary sources were rounded estimates, not
        # exact SOS pulls, and are excluded rather than presented as solid.
        "registration_snapshots": [
            {"date": "2024-10-01", "dem_lead": -295_455},
            {"date": "2025-07-01", "dem_lead": -327_398},
            {"date": "2026-07-01", "dem_lead": -318_734},
        ],
    },
    "mi": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 47.93, "incumbent_party": "R"},  # Snyder (inc) d. Schauer
            {"year": 2018, "dem_share": 54.93, "incumbent_party": None},  # Whitmer d. Schuette, open seat (Snyder term-limited)
            {"year": 2022, "dem_share": 55.35, "incumbent_party": "D"},  # Whitmer (inc) d. Dixon
        ],
        # Last 3 MI Senate elections (mixes Peters' seat, up in 2014/2020,
        # and Stabenow's now-open seat, up in 2024 -- a different seat from
        # this cycle's 2026 MI Senate race).
        "senate_elections": [
            {"year": 2014, "dem_share": 56.93},  # Peters d. Land, open seat (Levin retiring)
            {"year": 2020, "dem_share": 50.86},  # Peters (inc) d. James
            {"year": 2024, "dem_share": 50.18},  # Slotkin d. Rogers, open seat (Stabenow retiring)
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 49.88},  # Trump d. Clinton by 0.23 pts
            {"year": 2020, "dem_share": 51.41},  # Biden d. Trump
            {"year": 2024, "dem_share": 49.28},  # Trump d. Harris
        ],
        # Michigan doesn't register voters by party (a voter simply
        # requests a party's primary ballot each cycle, with no persistent
        # registration record) -- confirmed via Michigan SOS FAQ.
        "registration_snapshots": [],
    },
    "nh": {
        "gubernatorial_elections": [
            {"year": 2020, "dem_share": 33.88, "incumbent_party": "R"},  # Sununu (inc) d. Feltes; a real COVID-era rally-round-the-incumbent landslide, kept in the window (not discarded unilaterally)
            {"year": 2022, "dem_share": 42.12, "incumbent_party": "R"},  # Sununu (inc) d. Sherman
            {"year": 2024, "dem_share": 45.24, "incumbent_party": None},  # Ayotte d. Craig, open seat (Sununu retired)
        ],
        # NH's 2 Senate seats don't stagger evenly -- last 3 elections
        # chronologically across both seats (same convention as FL/GA/KS/NE/AZ).
        "senate_elections": [
            {"year": 2016, "dem_share": 50.07},  # Hassan d. Ayotte (inc) by just 1,017 votes -- a genuine toss-up, not an outlier to discard
            {"year": 2020, "dem_share": 58.02},  # Shaheen (inc) d. Messner, landslide
            {"year": 2022, "dem_share": 54.63},  # Hassan (inc) d. Bolduc
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 50.20},  # Clinton d. Trump
            {"year": 2020, "dem_share": 53.75},  # Biden d. Trump
            {"year": 2024, "dem_share": 51.41},  # Trump d. Harris
        ],
        # NH SOS publishes "Party Registration History." Real, well-documented
        # realignment: Democrats held a raw registration lead in 2020/2022,
        # but Republicans overtook them by the 2024 general and have held a
        # growing lead since (independently cross-checked: the May 2026
        # figure below was corroborated by a separate NH Journal report of
        # the same-period gap). "Undeclared" voters are the largest bloc in
        # every snapshot, a well-known NH structural feature.
        "registration_snapshots": [
            {"date": "2020-11-08", "dem_lead": 14_663},
            {"date": "2022-08-30", "dem_lead": 9_987},
            {"date": "2024-09-30", "dem_lead": -39_280},
            {"date": "2025-08-25", "dem_lead": -49_334},
            {"date": "2026-05-04", "dem_lead": -48_822},
        ],
    },
    "co": {
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 51.76, "incumbent_party": "D"},  # Hickenlooper (inc) d. Beauprez -- the closest of the 3, a near-toss-up by CO standards
            {"year": 2018, "dem_share": 55.51, "incumbent_party": None},  # Polis d. Stapleton, open seat (Hickenlooper term-limited)
            {"year": 2022, "dem_share": 59.90, "incumbent_party": "D"},  # Polis (inc) d. Ganahl -- a real landslide (Ganahl was a weak/underfunded challenger), flagged as the favorable-D outlier of the 3 but not discarded
        ],
        # CO's 2 Senate seats don't stagger evenly -- last 3 elections
        # chronologically across both seats (same convention as FL/GA/KS/NE/AZ/NH).
        "senate_elections": [
            {"year": 2016, "dem_share": 53.01},  # Bennet (inc) d. Glenn
            {"year": 2020, "dem_share": 54.77},  # Hickenlooper d. Gardner (inc), seat flip
            {"year": 2022, "dem_share": 57.53},  # Bennet (inc) d. O'Dea
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 52.68},  # Clinton d. Trump
            {"year": 2020, "dem_share": 56.94},  # Biden d. Trump
            {"year": 2024, "dem_share": 55.65},  # Trump d. Harris (still a real double-digit-two-party D win, just a smaller one)
        ],
        # CO SOS publishes monthly active-voter registration by party.
        # Real, well-documented trend: Democrats hold a stable raw lead over
        # Republicans (~87K-104K), but unaffiliated voters have grown from a
        # plurality to an outright majority of active registrants over this
        # span, so the D lead has shrunk as a *share* of the electorate even
        # while holding steady in raw count.
        "registration_snapshots": [
            {"date": "2020-08-01", "dem_lead": 87_311},
            {"date": "2022-08-01", "dem_lead": 103_358},
            {"date": "2024-07-01", "dem_lead": 104_181},
            {"date": "2026-07-01", "dem_lead": 98_161},
        ],
    },
    "vt": {
        # Phil Scott (R) has been the continuously-serving incumbent since
        # Jan. 2017 (won 2016/2018/2020/2022/2024) -- no open seat here.
        "gubernatorial_elections": [
            {"year": 2020, "dem_share": 27.35, "incumbent_party": "R"},  # Scott (inc) d. Zuckerman (Prog/Dem)
            {"year": 2022, "dem_share": 23.94, "incumbent_party": "R"},  # Scott (inc) d. Siegel
            {"year": 2024, "dem_share": 21.83, "incumbent_party": "R"},  # Scott (inc) d. Charlestin
        ],
        # VT's 2 Senate seats: Leahy/Welch's (Class I, up 2010/2016/2022) and
        # Sanders's (Class III, up 2006/2012/2018/2024). dem_share combines
        # independent-but-Democratic-caucusing Bernie Sanders's vote with the
        # Democratic column where relevant, same convention as Maine's Angus
        # King.
        "senate_elections": [
            {"year": 2018, "dem_share": 67.44},  # Sanders (I, caucuses D) d. Zupan
            {"year": 2022, "dem_share": 68.47},  # Welch d. Malloy, open seat (Leahy retired)
            {"year": 2024, "dem_share": 63.16},  # Sanders (I, caucuses D) d. Malloy
        ],
        # 2016 combines Clinton's 55.72% with Bernie Sanders's 5.68%
        # write-in share (a real, notable phenomenon in VT that year) for
        # 61.40% -- same Democratic-aligned-vote convention as the Senate
        # rows above and as Maine's King.
        "presidential_elections": [
            {"year": 2016, "dem_share": 61.4},  # Clinton (+ Sanders write-in) d. Trump
            {"year": 2020, "dem_share": 66.09},  # Biden d. Trump
            {"year": 2024, "dem_share": 63.83},  # Trump d. Harris (still a real double-digit-two-party D win, just a smaller one)
        ],
        # Vermont does not register voters by party (same as GA/OH) -- any
        # registered voter may vote in any one party's primary without
        # declaring membership, so there's no D-minus-R figure to track.
        "registration_snapshots": [],
        # Phil Scott is a constant, structural overperformer of VT's
        # Senate/presidential lean -- the state's federal races are
        # deeply Democratic (60s), but its own governor's races aren't
        # close. Per explicit direction, the gov/Senate/president split is
        # reweighted to 70/15/15 (vs. the global 45/30/25 default) so the
        # same-office signal dominates instead of being diluted by
        # Senate/presidential results that have never described this race.
        "model_overrides": {
            "gubernatorial_lean_weight": 0.70,
            "senate_lean_weight": 0.15,
        },
    },
    "ma": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 46.54, "incumbent_party": None},  
            {"year": 2018, "dem_share": 33.12, "incumbent_party": "R"},  
            {"year": 2022, "dem_share": 63.74, "incumbent_party": None},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 60.34}, 
            {"year": 2020, "dem_share": 66.15},  
            {"year": 2024, "dem_share": 59.81},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 60.01},  # Clinton d. Trump
            {"year": 2020, "dem_share": 65.60},  # Biden d. Trump
            {"year": 2024, "dem_share": 61.22},  # Trump d. Harris (still a real double-digit-two-party D win, just a smaller one)
        ],
       
        "registration_snapshots": [
            {"date": "2024-02-01", "dem_lead": 921_387},
            {"date": "2022-08-01", "dem_lead": 908_805},
            {"date": "2024-10-01", "dem_lead": 918_050},
            {"date": "2025-02-01", "dem_lead": 875_216},
        ],
    },
    "md": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 47.25, "incumbent_party": None},  
            {"year": 2018, "dem_share": 43.51, "incumbent_party": "R"},  
            {"year": 2022, "dem_share": 64.53, "incumbent_party": None},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 64.86}, 
            {"year": 2022, "dem_share": 65.77},  
            {"year": 2024, "dem_share": 54.64},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 60.33},  # Clinton d. Trump
            {"year": 2020, "dem_share": 65.36},  # Biden d. Trump
            {"year": 2024, "dem_share": 62.62},  # Trump d. Harris (still a real double-digit-two-party D win, just a smaller one)
        ],
       
        "registration_snapshots": [
            {"date": "2024-03-01", "dem_lead": 1_189_464},
            {"date": "2026-04-01", "dem_lead": 1_192_167},
            {"date": "2026-05-01", "dem_lead": 1_198_395},
            {"date": "2026-06-01", "dem_lead": 1_203_052},
        ],
    },
    "ca": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 59.97, "incumbent_party": "D"},  
            {"year": 2018, "dem_share": 61.95, "incumbent_party": None},  
            {"year": 2022, "dem_share": 59.18, "incumbent_party": "D"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 54.86}, 
            {"year": 2022, "dem_share": 61.09},  
            {"year": 2024, "dem_share": 58.87},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 61.73},  
            {"year": 2020, "dem_share": 63.48},  
            {"year": 2024, "dem_share": 58.47},  
        ],
       
        "registration_snapshots": [
            {"date": "2025-05-01", "dem_lead": 5_004_230},
            {"date": "2025-12-30", "dem_lead": 4_576_641},
        ],
    },
    "nm": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 42.78, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 57.20, "incumbent_party": None},  
            {"year": 2022, "dem_share": 51.97, "incumbent_party": "D"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 54.09}, 
            {"year": 2020, "dem_share": 53.14},  
            {"year": 2024, "dem_share": 55.06},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 54.65},  
            {"year": 2020, "dem_share": 55.51},  
            {"year": 2024, "dem_share": 53.07},  
        ],
       
        "registration_snapshots": [
            {"date": "2025-05-01", "dem_lead": 130_359},
            {"date": "2025-06-30", "dem_lead": 131_018},
            {"date": "2026-01-30", "dem_lead": 130_906},
        ],
    },
    "al": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 36.31, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 40.45, "incumbent_party": None},  
            {"year": 2022, "dem_share": 30.37, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2016, "dem_share": 35.93}, 
            {"year": 2020, "dem_share": 39.74},  
            {"year": 2022, "dem_share": 31.67},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 35.63},  
            {"year": 2020, "dem_share": 37.09},  
            {"year": 2024, "dem_share": 34.56},  
        ],
       
        "registration_snapshots": [],
    },
    "ar": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 42.80, "incumbent_party": None},  
            {"year": 2018, "dem_share": 32.72, "incumbent_party": "R"},  
            {"year": 2022, "dem_share": 35.86, "incumbent_party": None},  
      ],
   
        "senate_elections": [
            {"year": 2016, "dem_share": 37.70}, 
            {"year": 2020, "dem_share": 33.47},  
            {"year": 2022, "dem_share": 32.11},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 35.71},  
            {"year": 2020, "dem_share": 35.79},  
            {"year": 2024, "dem_share": 34.32},  
        ],
       
        "registration_snapshots": [],
    },
    "wi": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 47.13, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 50.56, "incumbent_party": "R"},  
            {"year": 2022, "dem_share": 51.72, "incumbent_party": "D"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 55.42}, 
            {"year": 2022, "dem_share": 49.50},  
            {"year": 2024, "dem_share": 50.43},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 49.59},  
            {"year": 2020, "dem_share": 50.32},  
            {"year": 2024, "dem_share": 49.56},  
        ],
       
        "registration_snapshots": [],
    },
    "id": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 41.87, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 38.99, "incumbent_party": None},  
            {"year": 2022, "dem_share": 37.47, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2016, "dem_share": 33.87}, 
            {"year": 2020, "dem_share": 34.68},  
            {"year": 2022, "dem_share": 37.19},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 31.68},  
            {"year": 2020, "dem_share": 34.12},  
            {"year": 2024, "dem_share": 31.24},  
        ],
       
        "registration_snapshots": [
            {"date": "2026-07-01", "dem_lead": -525_830},
        ],
    },
    "sd": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 26.51, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 48.29, "incumbent_party": None},  
            {"year": 2022, "dem_share": 36.20, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2016, "dem_share": 28.17}, 
            {"year": 2020, "dem_share": 27.30},  
            {"year": 2022, "dem_share": 32.14},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 34.03},  
            {"year": 2020, "dem_share": 36.57},  
            {"year": 2024, "dem_share": 35.07},  
        ],
       
        "registration_snapshots": [
            {"date": "2026-05-01", "dem_lead": -182_195},
            {"date": "2026-06-01", "dem_lead": -184_821},
        ],
    },
    "ok": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 42.35, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 43.34, "incumbent_party": None},  
            {"year": 2022, "dem_share": 42.98, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2016, "dem_share": 26.68}, 
            {"year": 2020, "dem_share": 24.24},  
            {"year": 2022, "dem_share": 33.29},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 30.69},  
            {"year": 2020, "dem_share": 33.75},  
            {"year": 2024, "dem_share": 32.53},  
        ],
       
        "registration_snapshots": [
            {"date": "2024-01-15", "dem_lead": -538_011},
            {"date": "2025-01-15", "dem_lead": -641_551},
        ],
    },
    "mn": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 52.93, "incumbent_party": "D"},  
            {"year": 2018, "dem_share": 55.93, "incumbent_party": None},  
            {"year": 2022, "dem_share": 53.95, "incumbent_party": "D"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 62.41}, 
            {"year": 2020, "dem_share": 52.84},  
            {"year": 2024, "dem_share": 58.11},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 50.84},  
            {"year": 2020, "dem_share": 53.64},  
            {"year": 2024, "dem_share": 52.17},  
        ],
       
        "registration_snapshots": []
    },

    "ct": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 51.29, "incumbent_party": "D"},  
            {"year": 2018, "dem_share": 51.65, "incumbent_party": None},  
            {"year": 2022, "dem_share": 56.55, "incumbent_party": "D"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 60.20}, 
            {"year": 2020, "dem_share": 57.45},  
            {"year": 2024, "dem_share": 58.61},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 57.14},  
            {"year": 2020, "dem_share": 60.19},  
            {"year": 2024, "dem_share": 57.38},  
        ],
       
        "registration_snapshots": [
            {"date": "2025-10-17", "dem_lead": 302_982}
        ]
    },
    "wy": {

      "gubernatorial_elections": [
            {"year": 2014, "dem_share": 31.45, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 29.09, "incumbent_party": None},  
            {"year": 2022, "dem_share": 17.60, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 31.01}, 
            {"year": 2020, "dem_share": 25.72},  
            {"year": 2024, "dem_share": 24.30},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 24.29},  
            {"year": 2020, "dem_share": 27.51},  
            {"year": 2024, "dem_share": 26.52},  
        ],
       
        "registration_snapshots": [
            {"date": "2026-07-01", "dem_lead": -181_975}
        ]
    },
    "ri": {
        # Ken Block is a legitimate independent polling ~20% -- there's no
        # real historical series to ground his fundamentals-only estimate
        # (fundamentals_vote_share hardcodes a flat 50% for any non-D/R
        # party, see fundamentals.py), so poll_weight_floor/ceiling are
        # pushed high to keep the blend anchored to real polling instead of
        # that fabricated placeholder, same mechanism VT uses (see below).
        "model_overrides": {"poll_weight_floor": 0.85, "poll_weight_ceiling": 0.9},
        "gubernatorial_elections": [
            {"year": 2014, "dem_share": 52.98, "incumbent_party": None},  
            {"year": 2018, "dem_share": 58.60, "incumbent_party": "D"},  
            {"year": 2022, "dem_share": 59.84, "incumbent_party": None},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 61.58}, 
            {"year": 2020, "dem_share": 66.48},  
            {"year": 2024, "dem_share": 60.05},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 58.31},  
            {"year": 2020, "dem_share": 60.60},  
            {"year": 2024, "dem_share": 57.08},  
        ],
       
        "registration_snapshots": [
            {"date": "2026-07-01", "dem_lead": 133_323}
        ]
    },

    "tn": {
         "gubernatorial_elections": [
            {"year": 2014, "dem_share": 24.51, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 39.29, "incumbent_party": None},  
            {"year": 2022, "dem_share": 33.64, "incumbent_party": "R"},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 44.53}, 
            {"year": 2020, "dem_share": 36.11},  
            {"year": 2024, "dem_share": 34.87},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 36.37},  
            {"year": 2020, "dem_share": 38.17},  
            {"year": 2024, "dem_share": 34.93},  
        ],
       
        "registration_snapshots": []
    },
    "hi": {
         "gubernatorial_elections": [
            {"year": 2014, "dem_share": 57.15, "incumbent_party": None},  
            {"year": 2018, "dem_share": 65.03, "incumbent_party": "D"},  
            {"year": 2022, "dem_share": 63.16, "incumbent_party": None},  
      ],
   
        "senate_elections": [
            {"year": 2018, "dem_share": 71.15}, 
            {"year": 2022, "dem_share": 73.23},  
            {"year": 2024, "dem_share": 66.95},  
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 67.44},  
            {"year": 2020, "dem_share": 65.03},  
            {"year": 2024, "dem_share": 61.78},  
        ],
       
        "registration_snapshots": []
    },
    "ak": {
         "gubernatorial_elections": [
            {"year": 2014, "dem_share": 51.81, "incumbent_party": "R"},  
            {"year": 2018, "dem_share": 46.33, "incumbent_party": None},  
            {"year": 2022, "dem_share": 32.49, "incumbent_party": "R"},  
      ],
   
        # 2016 (Murkowski d. Metcalfe/Stock) and 2022 (Murkowski d.
        # Tshibaka) are both excluded as outliers -- 2022's top-four RCV
        # system produced an all-Republican final round (Chesbro (D) was
        # eliminated early with a small first-round share), so there's no
        # non-Republican finalist whose share would represent the state's
        # Democratic-aligned coalition the way the fusion-ticket convention
        # does for AK's gubernatorial races. Left at a single election
        # (2020, Sullivan d. Gross) rather than backfilling further back,
        # per instruction.
        "senate_elections": [
            {"year": 2020, "dem_share": 43.31},
        ],
        "presidential_elections": [
            {"year": 2016, "dem_share": 41.61},  
            {"year": 2020, "dem_share": 44.74},  
            {"year": 2024, "dem_share": 43.16},  
        ],
       
        "registration_snapshots": []
    }
    
}

PRESIDENT = {
    "name": "Donald Trump",
    "party": "Republican",
    "approval_pct": 37.0,
    "as_of": "2026-07-10",
}

# Generic congressional ballot polling average, from the "Average" row of
# Wikipedia's 2026_United_States_House_of_Representatives_elections opinion
# polling table (fetched 2026-07-10). Real values -- not invented.
GENERIC_BALLOT = {
    "dem_pct": 47.8,
    "rep_pct": 42.0,
    "as_of": "2026-07-10",
    "source_url": "https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_elections",
}
