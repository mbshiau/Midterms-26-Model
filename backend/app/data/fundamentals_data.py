"""Real historical inputs for the fundamentals model (see app.services.fundamentals).

Sources:
- Historical PA gubernatorial results: Wikipedia/Ballotpedia/uselectionatlas
  results pages for each cited year. `dem_share` is Josh Shapiro-equivalent
  (Democratic candidate's) two-party vote share, i.e. renormalized to
  exclude third-party/write-in votes.
- Historical PA presidential results: Wikipedia's
  "United States presidential elections in Pennsylvania" and per-year
  election articles. Same two-party renormalization as the gubernatorial
  list.
- Registration snapshots: PA Department of State monthly registration
  statistics, as reported by Spotlight PA
  (spotlightpa.org/pennsylvania-voter-registration/ and its Sept 2024 /
  May 2026 coverage) and Pennsylvania Capital-Star. `dem_lead` is the
  statewide Democratic minus Republican registered-voter count.
- Presidential approval: aggregated national approval polling as of
  2026-07-10 (Silver Bulletin / FiftyPlusOne approval trackers), Trump
  (R), 2nd term.
"""

from datetime import date

ELECTION_DATE = date(2026, 11, 3)

# year, Democratic candidate's two-party vote share, which party (if any)
# held the seat as the incumbent running for reelection that year.
GUBERNATORIAL_ELECTIONS = [
    {"year": 2002, "dem_share": 54.64, "incumbent_party": None},  # Rendell d. Fisher, open seat
    {"year": 2006, "dem_share": 60.40, "incumbent_party": "D"},  # Rendell (inc) d. Swann
    {"year": 2010, "dem_share": 45.51, "incumbent_party": None},  # Onorato d. Corbett, open seat
    {"year": 2014, "dem_share": 54.90, "incumbent_party": "R"},  # Wolf d. Corbett (inc)
    {"year": 2018, "dem_share": 58.68, "incumbent_party": "D"},  # Wolf (inc) d. Wagner
    {"year": 2022, "dem_share": 56.24, "incumbent_party": None},  # Shapiro d. Mastriano, open seat
]

# Last 3 PA presidential results, same two-party-share convention. Trimmed
# from 6 to 3 cycles deliberately: PA's electorate has shifted enough since
# the Obama era (deindustrialization backlash, realignment of white
# working-class and college-educated voters) that 2004-2012 are judged too
# dated to usefully describe the state's current partisan lean.
PRESIDENTIAL_ELECTIONS = [
    {"year": 2016, "dem_share": 49.62},  # Trump d. Clinton (PA flipped R)
    {"year": 2020, "dem_share": 50.59},  # Biden d. Trump
    {"year": 2024, "dem_share": 49.14},  # Trump d. Harris
]

# Statewide registered-voter count, Democratic minus Republican.
REGISTRATION_SNAPSHOTS = [
    {"date": "2016-12-31", "dem_lead": 916_000},
    {"date": "2020-12-31", "dem_lead": 685_818},
    {"date": "2022-12-31", "dem_lead": 549_568},
    {"date": "2024-11-30", "dem_lead": 286_283},
    {"date": "2025-07-31", "dem_lead": 59_135},
    {"date": "2025-10-31", "dem_lead": 170_608},
    {"date": "2026-05-31", "dem_lead": 188_381},
]

PRESIDENT = {
    "name": "Donald Trump",
    "party": "Republican",
    "approval_pct": 37.0,
    "as_of": "2026-07-10",
}
