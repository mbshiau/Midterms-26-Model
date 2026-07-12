"""Real, publicly reported topline polling for each state's 2026 governor
race, keyed by state_code. Each race's polls are compiled from its Wikipedia
polling table plus each poll's own release where it could be located
independently.

`undecided_pct` is the complement (100 - candidate_a% - candidate_b%),
folding in any third-party/"other" share alongside true undecideds, since
this schema tracks only the two major-party candidates.
"""

PA_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Pennsylvania_gubernatorial_election"
OH_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Ohio_gubernatorial_election"
GA_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Georgia_gubernatorial_election"
NY_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_New_York_gubernatorial_election"
TX_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Texas_gubernatorial_election"
FL_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Florida_gubernatorial_election"
NV_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Nevada_gubernatorial_election"
IL_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Illinois_gubernatorial_election"
OR_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Oregon_gubernatorial_election"
MI_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Michigan_gubernatorial_election"
NE_WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Nebraska_gubernatorial_election"

RACES = {
    "pa": {
        "state_name": "Pennsylvania",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Pennsylvania_gubernatorial_election",
        "candidates": [
            {"name": "Josh Shapiro", "party": "Democratic", "incumbent": True},
            {"name": "Stacy Garrity", "party": "Republican", "incumbent": False},
        ],
        # Release dates for polls where the exact release day wasn't
        # confirmed in source reporting (both F&M polls, and the
        # PennLive/MAD Global Strategy polls) are reconstructed from
        # field-close + that outlet's typical turnaround (~2-5 days);
        # sample size, MoE, and toplines are all as published. PennLive and
        # MAD Global Strategy are sourced to the Wikipedia polling table
        # itself, since an independently reachable press release couldn't
        # be located for them.
        "raw_polls": [
            {
                "pollster": "Susquehanna Polling & Research",
                "sponsor": None,
                "field_start_date": "2025-09-22",
                "field_end_date": "2025-09-28",
                "release_date": "2025-10-03",
                "sample_size": 700,
                "population": "LV",
                "margin_of_error": 3.7,
                "undecided_pct": 10.0,
                "source_url": "https://www.newsweek.com/republicans-chances-defeating-josh-shapiro-pennsylvania-poll-10845075",
                "results": {"Josh Shapiro": 54.0, "Stacy Garrity": 36.0},
            },
            {
                "pollster": "Quinnipiac University",
                "sponsor": None,
                "field_start_date": "2025-09-25",
                "field_end_date": "2025-09-29",
                "release_date": "2025-10-01",
                "sample_size": 1579,
                "population": "RV",
                "margin_of_error": 3.3,
                "undecided_pct": 6.0,
                "source_url": "https://poll.qu.edu/poll-release?releaseid=3933",
                "results": {"Josh Shapiro": 55.0, "Stacy Garrity": 39.0},
            },
            {
                "pollster": "Franklin & Marshall College",
                "sponsor": None,
                "field_start_date": "2026-02-18",
                "field_end_date": "2026-03-01",
                "release_date": "2026-03-04",
                "sample_size": 834,
                "population": "RV",
                "margin_of_error": 4.1,
                "undecided_pct": 24.0,
                "source_url": "https://www.fandmpoll.org/franklin-marshall-poll-release-march-2026/",
                "results": {"Josh Shapiro": 48.0, "Stacy Garrity": 28.0},
            },
            {
                "pollster": "Quinnipiac University",
                "sponsor": None,
                "field_start_date": "2026-02-19",
                "field_end_date": "2026-02-23",
                "release_date": "2026-02-25",
                "sample_size": 836,
                "population": "RV",
                "margin_of_error": 4.7,
                "undecided_pct": 8.0,
                "source_url": "https://poll.qu.edu/poll-release?releaseid=3948",
                "results": {"Josh Shapiro": 55.0, "Stacy Garrity": 37.0},
            },
            {
                "pollster": "Susquehanna Polling & Research",
                "sponsor": None,
                "field_start_date": "2026-03-18",
                "field_end_date": "2026-03-29",
                "release_date": "2026-04-02",
                "sample_size": 700,
                "population": "LV",
                "margin_of_error": 3.7,
                "undecided_pct": 6.0,
                "source_url": "https://www.politicspa.com/susquehanna-poll-shapiro-holds-commanding-lead-over-garrity/146021/",
                "results": {"Josh Shapiro": 58.0, "Stacy Garrity": 36.0},
            },
            {
                "pollster": "PennLive",
                "sponsor": None,
                "field_start_date": "2026-05-20",
                "field_end_date": "2026-05-24",
                "release_date": "2026-05-28",
                "sample_size": 683,
                "population": "LV",
                "margin_of_error": 5.0,
                "undecided_pct": 18.0,
                "source_url": PA_WIKI_SOURCE,
                "results": {"Josh Shapiro": 53.0, "Stacy Garrity": 29.0},
            },
            {
                "pollster": "MAD Global Strategy",
                "sponsor": None,
                "field_start_date": "2026-06-09",
                "field_end_date": "2026-06-11",
                "release_date": "2026-06-13",
                "sample_size": 600,
                "population": "LV",
                "margin_of_error": 4.0,
                "undecided_pct": 21.0,
                "source_url": PA_WIKI_SOURCE,
                "results": {"Josh Shapiro": 48.0, "Stacy Garrity": 31.0},
            },
            {
                "pollster": "Franklin & Marshall College",
                "sponsor": None,
                "field_start_date": "2026-06-08",
                "field_end_date": "2026-06-14",
                "release_date": "2026-06-18",
                "sample_size": 546,
                "population": "RV",
                "margin_of_error": 5.1,
                "undecided_pct": 22.0,
                "source_url": "https://www.fandmpoll.org/franklin-marshall-college-poll-release-june-2026/",
                "results": {"Josh Shapiro": 50.0, "Stacy Garrity": 28.0},
            },
            {
                "pollster": "PennLive",
                "sponsor": None,
                "field_start_date": "2026-06-18",
                "field_end_date": "2026-06-25",
                "release_date": "2026-06-29",
                "sample_size": 644,
                "population": "RV",
                "margin_of_error": 4.14,
                "undecided_pct": 17.0,
                "source_url": PA_WIKI_SOURCE,
                "results": {"Josh Shapiro": 54.0, "Stacy Garrity": 29.0},
            },
        ],
    },
    "oh": {
        "state_name": "Ohio",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Ohio_gubernatorial_election",
        # Open seat: Mike DeWine (R) is term-limited. Ramaswamy declared
        # Feb 25, 2025; polls before that date tested a hypothetical
        # matchup and are cited to the Wikipedia polling table (no separate
        # press release located). All toplines/dates/samples as published.
        "candidates": [
            {"name": "Vivek Ramaswamy", "party": "Republican", "incumbent": False},
            {"name": "Amy Acton", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Public Policy Polling",
                "sponsor": "Democratic",
                "field_start_date": "2025-02-19",
                "field_end_date": "2025-02-20",
                "release_date": "2025-02-24",
                "sample_size": 642,
                "population": "RV",
                "margin_of_error": 3.9,
                "undecided_pct": 11.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 44.0, "Amy Acton": 45.0},
            },
            {
                "pollster": "Bowling Green State University/YouGov",
                "sponsor": None,
                "field_start_date": "2025-04-18",
                "field_end_date": "2025-04-24",
                "release_date": "2025-04-28",
                "sample_size": 800,
                "population": "RV",
                "margin_of_error": 4.1,
                "undecided_pct": 5.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 50.0, "Amy Acton": 45.0},
            },
            {
                "pollster": "Impact Research",
                "sponsor": "Democratic",
                "field_start_date": "2025-07-24",
                "field_end_date": "2025-07-28",
                "release_date": "2025-08-01",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.5,
                "undecided_pct": 7.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 47.0, "Amy Acton": 46.0},
            },
            {
                "pollster": "Emerson College",
                "sponsor": None,
                "field_start_date": "2025-08-18",
                "field_end_date": "2025-08-19",
                "release_date": "2025-08-21",
                "sample_size": 1000,
                "population": "RV",
                "margin_of_error": 3.0,
                "undecided_pct": 12.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 49.0, "Amy Acton": 39.0},
            },
            {
                "pollster": "Hart Research",
                "sponsor": "Democratic",
                "field_start_date": "2025-09-19",
                "field_end_date": "2025-09-22",
                "release_date": "2025-09-26",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.0,
                "undecided_pct": 9.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 45.0, "Amy Acton": 46.0},
            },
            {
                "pollster": "Bowling Green State University/YouGov",
                "sponsor": None,
                "field_start_date": "2025-10-02",
                "field_end_date": "2025-10-14",
                "release_date": "2025-10-18",
                "sample_size": 800,
                "population": "RV",
                "margin_of_error": 4.5,
                "undecided_pct": 3.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 50.0, "Amy Acton": 47.0},
            },
            {
                "pollster": "Data Targeting",
                "sponsor": "Republican",
                "field_start_date": "2025-12-03",
                "field_end_date": "2025-12-08",
                "release_date": "2025-12-12",
                "sample_size": 603,
                "population": "LV",
                "margin_of_error": 4.0,
                "undecided_pct": 12.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 45.0, "Amy Acton": 43.0},
            },
            {
                "pollster": "Emerson College",
                "sponsor": None,
                "field_start_date": "2025-12-06",
                "field_end_date": "2025-12-08",
                "release_date": "2025-12-10",
                "sample_size": 850,
                "population": "RV",
                "margin_of_error": 3.3,
                "undecided_pct": 9.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 45.0, "Amy Acton": 46.0},
            },
            {
                "pollster": "EMC Research",
                "sponsor": "Democratic",
                "field_start_date": "2026-02-10",
                "field_end_date": "2026-02-22",
                "release_date": "2026-02-26",
                "sample_size": 1343,
                "population": "LV",
                "margin_of_error": 2.7,
                "undecided_pct": 4.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 43.0, "Amy Acton": 53.0},
            },
            {
                "pollster": "Quantus Insights",
                "sponsor": "Republican",
                "field_start_date": "2026-03-13",
                "field_end_date": "2026-03-14",
                "release_date": "2026-03-17",
                "sample_size": 809,
                "population": "LV",
                "margin_of_error": 3.8,
                "undecided_pct": 9.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 45.0, "Amy Acton": 46.0},
            },
            {
                "pollster": "Echelon Insights",
                "sponsor": "Republican",
                "field_start_date": "2026-04-03",
                "field_end_date": "2026-04-09",
                "release_date": "2026-04-12",
                "sample_size": 413,
                "population": "LV",
                "margin_of_error": 5.8,
                "undecided_pct": 7.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 49.0, "Amy Acton": 44.0},
            },
            {
                "pollster": "Bowling Green State University/YouGov",
                "sponsor": None,
                "field_start_date": "2026-04-07",
                "field_end_date": "2026-04-14",
                "release_date": "2026-04-18",
                "sample_size": 1000,
                "population": "RV",
                "margin_of_error": 4.5,
                "undecided_pct": 5.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 48.0, "Amy Acton": 47.0},
            },
            {
                "pollster": "Beacon Research/Shaw & Co. Research",
                "sponsor": None,
                "field_start_date": "2026-05-28",
                "field_end_date": "2026-06-01",
                "release_date": "2026-06-04",
                "sample_size": 1015,
                "population": "RV",
                "margin_of_error": 3.0,
                "undecided_pct": 1.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 49.0, "Amy Acton": 50.0},
            },
            {
                "pollster": "Tulchin Research",
                "sponsor": "Democratic",
                "field_start_date": "2026-06-02",
                "field_end_date": "2026-06-04",
                "release_date": "2026-06-07",
                "sample_size": 600,
                "population": "LV",
                "margin_of_error": 4.0,
                "undecided_pct": 9.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 44.0, "Amy Acton": 47.0},
            },
            {
                "pollster": "Fabrizio Ward/Impact Research",
                "sponsor": "AARP",
                "field_start_date": "2026-06-14",
                "field_end_date": "2026-06-16",
                "release_date": "2026-06-19",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.5,
                "undecided_pct": 9.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 44.0, "Amy Acton": 47.0},
            },
            {
                "pollster": "New York Times/Siena University",
                "sponsor": None,
                "field_start_date": "2026-06-15",
                "field_end_date": "2026-06-28",
                "release_date": "2026-07-01",
                "sample_size": 601,
                "population": "LV",
                "margin_of_error": 4.7,
                "undecided_pct": 6.0,
                "source_url": OH_WIKI_SOURCE,
                "results": {"Vivek Ramaswamy": 47.0, "Amy Acton": 47.0},
            },
        ],
    },
    "ga": {
        "state_name": "Georgia",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Georgia_gubernatorial_election",
        # Open seat: Brian Kemp (R) is term-limited. General campaign only
        # began after the June 16 runoff, so the polling table is short so
        # far. All cited to the Wikipedia polling table itself, since a
        # separate press release wasn't located for any of them.
        "candidates": [
            {"name": "Rick Jackson", "party": "Republican", "incumbent": False},
            {"name": "Keisha Lance Bottoms", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Echelon Insights",
                "sponsor": "Republican",
                "field_start_date": "2026-04-03",
                "field_end_date": "2026-04-09",
                "release_date": "2026-04-13",
                "sample_size": 407,
                "population": "LV",
                "margin_of_error": 6.5,
                "undecided_pct": 8.0,
                "source_url": GA_WIKI_SOURCE,
                "results": {"Rick Jackson": 43.0, "Keisha Lance Bottoms": 49.0},
            },
            {
                "pollster": "Concord Public Opinion Partners",
                "sponsor": "Democratic",
                "field_start_date": "2026-05-30",
                "field_end_date": "2026-06-02",
                "release_date": "2026-06-05",
                "sample_size": 510,
                "population": "LV",
                "margin_of_error": 4.3,
                "undecided_pct": 9.0,
                "source_url": GA_WIKI_SOURCE,
                "results": {"Rick Jackson": 38.0, "Keisha Lance Bottoms": 53.0},
            },
            {
                "pollster": "Beacon Research/Shaw & Co. Research",
                "sponsor": None,
                "field_start_date": "2026-06-23",
                "field_end_date": "2026-06-27",
                "release_date": "2026-06-30",
                "sample_size": 1002,
                "population": "RV",
                "margin_of_error": 3.0,
                "undecided_pct": 1.0,
                "source_url": GA_WIKI_SOURCE,
                "results": {"Rick Jackson": 47.0, "Keisha Lance Bottoms": 52.0},
            },
            {
                "pollster": "Wick",
                "sponsor": None,
                "field_start_date": "2026-06-27",
                "field_end_date": "2026-06-30",
                "release_date": "2026-07-03",
                "sample_size": 1175,
                "population": "LV",
                "margin_of_error": 2.9,
                "undecided_pct": 14.0,
                "source_url": GA_WIKI_SOURCE,
                "results": {"Rick Jackson": 43.0, "Keisha Lance Bottoms": 43.0},
            },
        ],
    },
    "me": {
        "state_name": "Maine",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Maine_gubernatorial_election",
        # Open seat: Janet Mills (D) is term-limited (Maine caps governors at
        # 2 consecutive terms). Both parties' nominations were settled by
        # Maine's standard ranked-choice-voting primary on June 9-19, 2026:
        # Pingree defeated Nirav Shah in the Democratic primary, and Charles
        # defeated Ben Midgley in the Republican primary. (A separate,
        # non-binding April 25 GOP convention straw poll was won by Midgley,
        # not Charles -- that straw poll wasn't the actual nomination.)
        # Independent state Sen. Rick Bennett (a former Maine Senate
        # president and former state GOP chair) also qualified for the
        # November ballot; both polls below tested a Pingree-vs-Charles
        # head-to-head (the NYT/Siena poll separately tested a 3-way
        # question with Bennett at 8%, not used here), so Bennett's support
        # is folded into undecided_pct along with true undecideds, the same
        # convention used for third-party/"Other" shares in PA/OH/GA.
        "candidates": [
            {"name": "Bobby Charles", "party": "Republican", "incumbent": False},
            {"name": "Hannah Pingree", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Fox News/Beacon Research/Shaw & Co. Research",
                "sponsor": None,
                "field_start_date": "2026-06-23",
                "field_end_date": "2026-06-27",
                "release_date": "2026-06-30",
                "sample_size": 1003,
                "population": "RV",
                "margin_of_error": 3.0,
                "undecided_pct": 5.0,
                "source_url": "https://static.foxnews.com/foxnews.com/content/uploads/2026/06/fox_june-23-27-2026_complete_maine_topline_june-30-release.pdf",
                "results": {"Bobby Charles": 42.0, "Hannah Pingree": 53.0},
            },
            {
                "pollster": "New York Times/Portland Press Herald/Siena University",
                "sponsor": None,
                "field_start_date": "2026-06-19",
                "field_end_date": "2026-06-26",
                "release_date": "2026-06-30",
                "sample_size": 608,
                "population": "LV",
                "margin_of_error": 4.8,
                "undecided_pct": 5.0,
                "source_url": "https://www.pressherald.com/2026/06/30/hannah-pingree-is-the-heavy-favorite-in-maine-governors-race-times-press-herald-siena-poll-finds/",
                "results": {"Bobby Charles": 40.0, "Hannah Pingree": 55.0},
            },
        ],
    },
    "ia": {
        "state_name": "Iowa",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Iowa_gubernatorial_election",
        # Open seat: Kim Reynolds (R) announced in April 2025 she would not
        # seek a third full term. The June 2, 2026 primary settled both
        # nominations: Zach Lahn (R) narrowly upset Trump-endorsed Rep. Randy
        # Feenstra, and Rob Sand (D, state auditor) ran unopposed.
        "candidates": [
            {"name": "Zach Lahn", "party": "Republican", "incumbent": False},
            {"name": "Rob Sand", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Siena College/New York Times",
                "sponsor": None,
                "field_start_date": "2026-06-15",
                "field_end_date": "2026-06-27",
                "release_date": "2026-07-01",
                "sample_size": 600,
                "population": "LV",
                "margin_of_error": 5.0,
                "undecided_pct": 5.0,
                "source_url": "https://www.thegazette.com/news/elections/national/polls-iowa-s-u-s-senate-campaign-tight-sand-leads-for-governor/article_c9e86be1-a2cc-4dfe-a417-a6a3270388e6.html",
                "results": {"Zach Lahn": 47.0, "Rob Sand": 48.0},
            },
            {
                "pollster": "Fox News/Beacon Research/Shaw & Co. Research",
                "sponsor": None,
                "field_start_date": "2026-06-23",
                "field_end_date": "2026-06-27",
                "release_date": "2026-07-01",
                "sample_size": 1003,
                "population": "RV",
                "margin_of_error": 3.0,
                "undecided_pct": 3.0,
                "source_url": "https://static.foxnews.com/foxnews.com/content/uploads/2026/07/fox_june-23-27-2026_complete_iowa_topline_july-1-release.pdf",
                "results": {"Zach Lahn": 44.0, "Rob Sand": 53.0},
            },
        ],
    },
    "ny": {
        "state_name": "New York",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_New_York_gubernatorial_election",
        # Incumbent Kathy Hochul (D) is running for reelection; Lt. Gov.
        # Antonio Delgado's primary challenge fizzled and he withdrew Feb
        # 10, 2026. Bruce Blakeman (R), Nassau County executive, is the
        # Republican nominee (Rep. Elise Stefanik withdrew from that primary
        # Dec 19, 2025). Both ran unopposed in the June 23, 2026 primary.
        "candidates": [
            {"name": "Bruce Blakeman", "party": "Republican", "incumbent": False},
            {"name": "Kathy Hochul", "party": "Democratic", "incumbent": True},
        ],
        # Only polls fielded after Stefanik's Dec 19, 2025 withdrawal are
        # used, since earlier polls tested a hypothetical Hochul-vs-Stefanik
        # matchup rather than the real nominees. Exact release dates are
        # cited where an original press release/PDF was located (all 3
        # Siena releases used here); where only the field dates were
        # confirmed, release_date is approximated as field_end + a few days
        # (that pollster's typical turnaround) and cited to the Wikipedia
        # polling table itself, same convention used for PA's PennLive/MAD
        # Global Strategy polls.
        "raw_polls": [
            {
                "pollster": "Siena College",
                "sponsor": None,
                "field_start_date": "2026-01-26",
                "field_end_date": "2026-01-28",
                "release_date": "2026-02-02",
                "sample_size": 802,
                "population": "RV",
                "margin_of_error": 4.3,
                "undecided_pct": 18.0,
                "source_url": NY_WIKI_SOURCE,
                "results": {"Bruce Blakeman": 28.0, "Kathy Hochul": 54.0},
            },
            {
                "pollster": "Marist University",
                "sponsor": None,
                "field_start_date": "2026-02-16",
                "field_end_date": "2026-02-19",
                "release_date": "2026-02-23",
                "sample_size": 1442,
                "population": "RV",
                "margin_of_error": 3.3,
                "undecided_pct": 17.0,
                "source_url": "https://maristpoll.marist.edu/polls/the-state-of-new-york-in-an-election-year-february-2026/",
                "results": {"Bruce Blakeman": 33.0, "Kathy Hochul": 50.0},
            },
            {
                "pollster": "Siena College",
                "sponsor": None,
                "field_start_date": "2026-02-23",
                "field_end_date": "2026-02-26",
                "release_date": "2026-03-02",
                "sample_size": 805,
                "population": "RV",
                "margin_of_error": 4.5,
                "undecided_pct": 18.0,
                "source_url": NY_WIKI_SOURCE,
                "results": {"Bruce Blakeman": 31.0, "Kathy Hochul": 51.0},
            },
            {
                "pollster": "McLaughlin & Associates",
                "sponsor": "Republican",
                "field_start_date": "2026-03-04",
                "field_end_date": "2026-03-08",
                "release_date": "2026-03-11",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.5,
                "undecided_pct": 5.0,
                "source_url": NY_WIKI_SOURCE,
                "results": {"Bruce Blakeman": 43.0, "Kathy Hochul": 52.0},
            },
            {
                "pollster": "Siena College",
                "sponsor": None,
                "field_start_date": "2026-03-23",
                "field_end_date": "2026-03-26",
                "release_date": "2026-03-31",
                "sample_size": 804,
                "population": "RV",
                "margin_of_error": 4.5,
                "undecided_pct": 19.0,
                "source_url": "https://sri.siena.edu/2026/03/31/hochul-lead-over-still-largely-unknown-blakeman-drops-7-points-to-47-34-from-51-31-her-favorability-approval-ratings-unchanged-in-last-month/",
                "results": {"Bruce Blakeman": 34.0, "Kathy Hochul": 47.0},
            },
            {
                "pollster": "Siena College",
                "sponsor": None,
                "field_start_date": "2026-04-27",
                "field_end_date": "2026-04-30",
                "release_date": "2026-05-05",
                "sample_size": 806,
                "population": "RV",
                "margin_of_error": 4.2,
                "undecided_pct": 18.0,
                "source_url": "https://sri.siena.edu/2026/05/05/hochul-favorability-approval-ratings-each-drop-8-points-to-lowest-levels-in-last-year-her-lead-over-blakeman-grows-3-points-to-49-33/",
                "results": {"Bruce Blakeman": 33.0, "Kathy Hochul": 49.0},
            },
            {
                "pollster": "Pollfinity Research",
                "sponsor": None,
                "field_start_date": "2026-06-11",
                "field_end_date": "2026-06-14",
                "release_date": "2026-06-17",
                "sample_size": 229,
                "population": "RV",
                "margin_of_error": 6.5,
                "undecided_pct": 10.0,
                "source_url": "https://www.opinionsandratings.com/picks-for-you/new-york-governor-election-polls",
                "results": {"Bruce Blakeman": 40.0, "Kathy Hochul": 50.0},
            },
            {
                "pollster": "Siena College",
                "sponsor": None,
                "field_start_date": "2026-06-17",
                "field_end_date": "2026-06-23",
                "release_date": "2026-06-25",
                "sample_size": 1120,
                "population": "RV",
                "margin_of_error": 3.6,
                "undecided_pct": 16.0,
                "source_url": "https://sri.siena.edu/2026/06/25/hochul-favorability-approval-ratings-edge-up-as-does-her-general-election-lead-over-blakeman-now-52-32-from-49-33/",
                "results": {"Bruce Blakeman": 32.0, "Kathy Hochul": 52.0},
            },
            {
                "pollster": "co/efficient",
                "sponsor": "Republican",
                "field_start_date": "2026-06-30",
                "field_end_date": "2026-07-02",
                "release_date": "2026-07-06",
                "sample_size": 1085,
                "population": "LV",
                "margin_of_error": 3.0,
                "undecided_pct": 12.0,
                "source_url": NY_WIKI_SOURCE,
                "results": {"Bruce Blakeman": 41.0, "Kathy Hochul": 47.0},
            },
        ],
    },
    "sc": {
        "state_name": "South Carolina",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_South_Carolina_gubernatorial_election",
        # Open seat: Henry McMaster (R) is barred from a third consecutive
        # elected term. AG Alan Wilson (R) defeated Lt. Gov. Pamela Evette in
        # a June 23, 2026 runoff after the June 9 primary; state Rep.
        # Jermaine Johnson (D) won his primary outright. No third-party/
        # independent complication in this matchup.
        "candidates": [
            {"name": "Alan Wilson", "party": "Republican", "incumbent": False},
            {"name": "Jermaine Johnson", "party": "Democratic", "incumbent": False},
        ],
        # No real general-election trial-heat poll of Wilson vs. Johnson has
        # been published as of 2026-07-11 -- the runoff was barely 3 weeks
        # ago. Left empty rather than substituting the primary/runoff polls
        # (which measured a different, intra-Republican electorate) or
        # fabricating one; the forecast falls back to a fundamentals-only
        # estimate (see app.services.forecasting.generate_forecast) until a
        # real poll is published and picked up by the live scraper.
        "raw_polls": [],
    },
    "tx": {
        "state_name": "Texas",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Texas_gubernatorial_election",
        # Abbott (R) is running for a 4th term (no TX gubernatorial term
        # limits), won the March 3, 2026 primary outright with 82%. State
        # Rep. Gina Hinojosa (D) won a 9-way Democratic primary with 59%, no
        # runoff needed. Both nominations settled well before today.
        "candidates": [
            {"name": "Greg Abbott", "party": "Republican", "incumbent": True},
            {"name": "Gina Hinojosa", "party": "Democratic", "incumbent": False},
        ],
        # Release dates aren't independently confirmed for most of these
        # (only field dates were), so they're approximated as field_end + a
        # few days' typical turnaround and cited to the Wikipedia polling
        # table itself (cross-checked against its raw wikitext, which
        # carries per-row citations to each pollster's own release).
        "raw_polls": [
            {
                "pollster": "Siena College/New York Times",
                "sponsor": None,
                "field_start_date": "2026-06-19",
                "field_end_date": "2026-06-27",
                "release_date": "2026-06-30",
                "sample_size": 656,
                "population": "LV",
                "margin_of_error": 4.5,
                "undecided_pct": 5.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 51.0, "Gina Hinojosa": 44.0},
            },
            {
                "pollster": "SoCal Strategies",
                "sponsor": "Republican",
                "field_start_date": "2026-06-21",
                "field_end_date": "2026-06-21",
                "release_date": "2026-06-24",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": None,
                "undecided_pct": 4.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 54.0, "Gina Hinojosa": 42.0},
            },
            {
                "pollster": "University of Texas/Texas Politics Project",
                "sponsor": None,
                "field_start_date": "2026-06-05",
                "field_end_date": "2026-06-12",
                "release_date": "2026-06-15",
                "sample_size": 1200,
                "population": "RV",
                "margin_of_error": 2.8,
                "undecided_pct": 13.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 47.0, "Gina Hinojosa": 40.0},
            },
            {
                "pollster": "Quantus Insights",
                "sponsor": "Republican",
                "field_start_date": "2026-06-03",
                "field_end_date": "2026-06-04",
                "release_date": "2026-06-07",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.5,
                "undecided_pct": 10.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 49.0, "Gina Hinojosa": 41.0},
            },
            {
                "pollster": "Texas A&M University/ReconMR",
                "sponsor": None,
                "field_start_date": "2026-06-01",
                "field_end_date": "2026-06-04",
                "release_date": "2026-06-07",
                "sample_size": 807,
                "population": "LV",
                "margin_of_error": 4.0,
                "undecided_pct": 8.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 49.0, "Gina Hinojosa": 43.0},
            },
            {
                "pollster": "Slingshot Strategies",
                "sponsor": "Democratic",
                "field_start_date": "2026-05-27",
                "field_end_date": "2026-05-28",
                "release_date": "2026-05-31",
                "sample_size": 1670,
                "population": "LV",
                "margin_of_error": 2.8,
                "undecided_pct": 13.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 46.0, "Gina Hinojosa": 41.0},
            },
            {
                "pollster": "Public Policy Polling",
                "sponsor": "Democratic",
                "field_start_date": "2026-05-22",
                "field_end_date": "2026-05-23",
                "release_date": "2026-05-26",
                "sample_size": 643,
                "population": "RV",
                "margin_of_error": None,
                "undecided_pct": 8.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 48.0, "Gina Hinojosa": 44.0},
            },
            {
                "pollster": "Texas Southern University/YouGov",
                "sponsor": None,
                "field_start_date": "2026-04-22",
                "field_end_date": "2026-05-05",
                "release_date": "2026-05-08",
                "sample_size": 1223,
                "population": "LV",
                "margin_of_error": 2.8,
                "undecided_pct": 8.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 49.0, "Gina Hinojosa": 43.0},
            },
            {
                "pollster": "Slingshot Strategies",
                "sponsor": "Democratic",
                "field_start_date": "2026-04-17",
                "field_end_date": "2026-04-20",
                "release_date": "2026-04-23",
                "sample_size": 1018,
                "population": "LV",
                "margin_of_error": 3.3,
                "undecided_pct": 9.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 48.0, "Gina Hinojosa": 43.0},
            },
            {
                "pollster": "University of Texas/Texas Politics Project",
                "sponsor": None,
                "field_start_date": "2026-04-10",
                "field_end_date": "2026-04-20",
                "release_date": "2026-04-23",
                "sample_size": 1200,
                "population": "RV",
                "margin_of_error": 2.8,
                "undecided_pct": 18.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 44.0, "Gina Hinojosa": 38.0},
            },
            {
                "pollster": "UT Tyler",
                "sponsor": None,
                "field_start_date": "2026-02-13",
                "field_end_date": "2026-02-22",
                "release_date": "2026-02-25",
                "sample_size": 1117,
                "population": "RV",
                "margin_of_error": 3.1,
                "undecided_pct": 10.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 49.0, "Gina Hinojosa": 41.0},
            },
            {
                "pollster": "University of Texas/Texas Politics Project",
                "sponsor": None,
                "field_start_date": "2026-02-02",
                "field_end_date": "2026-02-16",
                "release_date": "2026-02-19",
                "sample_size": 1300,
                "population": "RV",
                "margin_of_error": 5.1,
                "undecided_pct": 20.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 45.0, "Gina Hinojosa": 35.0},
            },
            {
                "pollster": "GBAO",
                "sponsor": "Democratic",
                "field_start_date": "2026-01-26",
                "field_end_date": "2026-02-03",
                "release_date": "2026-02-06",
                "sample_size": 1000,
                "population": "LV",
                "margin_of_error": 3.1,
                "undecided_pct": 11.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 46.0, "Gina Hinojosa": 43.0},
            },
            {
                "pollster": "University of Houston/YouGov",
                "sponsor": None,
                "field_start_date": "2026-01-20",
                "field_end_date": "2026-01-31",
                "release_date": "2026-02-03",
                "sample_size": 1502,
                "population": "LV",
                "margin_of_error": 2.5,
                "undecided_pct": 9.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 49.0, "Gina Hinojosa": 42.0},
            },
            {
                "pollster": "Emerson College",
                "sponsor": None,
                "field_start_date": "2026-01-10",
                "field_end_date": "2026-01-12",
                "release_date": "2026-01-15",
                "sample_size": 1165,
                "population": "RV",
                "margin_of_error": 2.8,
                "undecided_pct": 8.0,
                "source_url": TX_WIKI_SOURCE,
                "results": {"Greg Abbott": 50.0, "Gina Hinojosa": 42.0},
            },
        ],
    },
    "fl": {
        "state_name": "Florida",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Florida_gubernatorial_election",
        # Open seat: Ron DeSantis (R) is term-limited. Neither primary is
        # LEGALLY decided yet -- Florida's primary is August 18, 2026,
        # still weeks away as of this writing -- but Byron Donalds (R,
        # Trump-endorsed) and David Jolly (D, a former Republican
        # congressman who became a Democrat) are used as presumptive
        # nominees per explicit direction: Donalds dominates every neutral
        # poll against his declared primary rivals (Lt. Gov. Jay Collins,
        # ex-House Speaker Paul Renner), and Jolly's only serious rival
        # (Orange County Mayor Jerry Demings) suspended his campaign June
        # 5, 2026 after a cancer diagnosis, leaving only minor candidates.
        "candidates": [
            {"name": "Byron Donalds", "party": "Republican", "incumbent": False},
            {"name": "David Jolly", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "James Madison Institute",
                "sponsor": "Republican",
                "field_start_date": "2026-02-13",
                "field_end_date": "2026-02-16",
                "release_date": "2026-02-19",
                "sample_size": 1200,
                "population": "RV",
                "margin_of_error": 2.77,
                "undecided_pct": 23.0,
                "source_url": "https://floridapolitics.com/archives/758095-byron-donalds-paul-renner-both-hold-edge-barely-over-david-jolly-in-poll-from-jmi/",
                "results": {"Byron Donalds": 41.0, "David Jolly": 36.0},
            },
            {
                "pollster": "Emerson College",
                "sponsor": None,
                "field_start_date": "2026-03-29",
                "field_end_date": "2026-03-31",
                "release_date": "2026-04-03",
                "sample_size": 1125,
                "population": "LV",
                "margin_of_error": 2.8,
                "undecided_pct": 17.0,
                "source_url": "https://emersoncollegepolling.com/florida-2026-poll-donalds-leads-gop-primary-for-governor-republicans-outpace-democrats-in-florida-elections/",
                "results": {"Byron Donalds": 44.0, "David Jolly": 39.0},
            },
            {
                "pollster": "Change Research",
                "sponsor": None,
                "field_start_date": "2026-05-13",
                "field_end_date": "2026-05-16",
                "release_date": "2026-05-19",
                "sample_size": 1593,
                "population": "LV",
                "margin_of_error": None,
                "undecided_pct": 12.0,
                "source_url": "https://changeresearch.com/florida-governors-race-may-2026/",
                "results": {"Byron Donalds": 42.0, "David Jolly": 46.0},
            },
            {
                "pollster": "Change Research",
                # Sponsor listed as "Freedom Project USA" in the release,
                # but its political orientation couldn't be independently
                # confirmed -- left unset rather than asserting a lean.
                "sponsor": None,
                "field_start_date": "2026-06-11",
                "field_end_date": "2026-06-14",
                "release_date": "2026-06-17",
                "sample_size": 1015,
                "population": "LV",
                "margin_of_error": None,
                "undecided_pct": 8.0,
                "source_url": "https://changeresearch.com/wp-content/uploads/2026/06/Florida-June-Poll-Memo.pdf",
                "results": {"Byron Donalds": 43.0, "David Jolly": 49.0},
            },
        ],
    },
    "nv": {
        "state_name": "Nevada",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Nevada_gubernatorial_election",
        # Incumbent Joe Lombardo (R) won his June 9, 2026 primary with ~91%.
        # AG Aaron Ford (D) won the Democratic primary with ~64% over Washoe
        # County Commission Chair Alexis Hill. Both settled well before
        # today. Nevada's unique "None of These Candidates" ballot line
        # appeared in both primaries but isn't modeled as a candidate here,
        # same convention as folding minor shares into undecided_pct.
        "candidates": [
            {"name": "Joe Lombardo", "party": "Republican", "incumbent": True},
            {"name": "Aaron Ford", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Noble Predictive Insights",
                "sponsor": None,
                "field_start_date": "2025-10-07",
                "field_end_date": "2025-10-13",
                "release_date": "2025-10-17",
                "sample_size": 766,
                "population": "RV",
                "margin_of_error": 3.5,
                "undecided_pct": 23.0,
                "source_url": NV_WIKI_SOURCE,
                "results": {"Joe Lombardo": 40.0, "Aaron Ford": 37.0},
            },
            {
                "pollster": "Emerson College",
                "sponsor": None,
                "field_start_date": "2025-11-16",
                "field_end_date": "2025-11-18",
                "release_date": "2025-11-21",
                "sample_size": 800,
                "population": "RV",
                "margin_of_error": 3.4,
                "undecided_pct": 18.0,
                "source_url": "https://emersoncollegepolling.com/nevada-2026-poll/",
                "results": {"Joe Lombardo": 41.0, "Aaron Ford": 41.0},
            },
            {
                "pollster": "Hart Research",
                "sponsor": "Democratic",
                "field_start_date": "2026-02-11",
                "field_end_date": "2026-02-17",
                "release_date": "2026-02-20",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": None,
                "undecided_pct": 12.0,
                "source_url": "https://thenevadaindependent.com/article/lombardo-remains-popular-but-new-dem-poll-ids-vulnerabilities-a-year-before-re-election",
                "results": {"Joe Lombardo": 45.0, "Aaron Ford": 43.0},
            },
            {
                "pollster": "Noble Predictive Insights",
                "sponsor": None,
                "field_start_date": "2026-03-10",
                "field_end_date": "2026-03-13",
                "release_date": "2026-03-17",
                "sample_size": 845,
                "population": "RV",
                "margin_of_error": 3.4,
                "undecided_pct": 23.0,
                "source_url": "https://www.noblepredictiveinsights.com/post/nvgov-lombardo-keeps-pace-with-ford-as-undecideds-hold-the-balance",
                "results": {"Joe Lombardo": 39.0, "Aaron Ford": 38.0},
            },
            {
                "pollster": "Global Strategy Group",
                "sponsor": "Democratic",
                "field_start_date": "2026-05-05",
                "field_end_date": "2026-05-11",
                "release_date": "2026-05-15",
                "sample_size": 700,
                "population": "LV",
                "margin_of_error": 3.7,
                "undecided_pct": 13.0,
                "source_url": NV_WIKI_SOURCE,
                "results": {"Joe Lombardo": 45.0, "Aaron Ford": 42.0},
            },
        ],
    },
    "il": {
        "state_name": "Illinois",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Illinois_gubernatorial_election",
        # Incumbent JB Pritzker (D), running for a 3rd term, was unopposed
        # in the March 17, 2026 Democratic primary. Darren Bailey (R, the
        # 2022 nominee) won the Republican primary with 54% -- a rematch of
        # 2022, the first IL gubernatorial rematch since 1986. National
        # 2028-presidential speculation around Pritzker is real but doesn't
        # conflict with this race (different election cycle).
        "candidates": [
            {"name": "JB Pritzker", "party": "Democratic", "incumbent": True},
            {"name": "Darren Bailey", "party": "Republican", "incumbent": False},
        ],
        # Only one real 2026 general-election trial-heat poll was located;
        # several widely-syndicated "Pritzker vs. Bailey" numbers found in
        # search results are actually from the 2022 race and were excluded
        # rather than mistakenly reused for 2026.
        "raw_polls": [
            {
                "pollster": "Victory Research",
                "sponsor": None,
                "field_start_date": "2025-11-20",
                "field_end_date": "2025-11-25",
                "release_date": "2025-11-26",
                "sample_size": 1208,
                "population": "LV",
                "margin_of_error": 2.82,
                "undecided_pct": 11.7,
                "source_url": "https://www.fox32chicago.com/news/illinois-jb-pritzker-poll-nov-25",
                "results": {"JB Pritzker": 54.3, "Darren Bailey": 34.0},
            },
        ],
    },
    "or": {
        "state_name": "Oregon",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Oregon_gubernatorial_election",
        # Incumbent Tina Kotek (D) won her May 19, 2026 primary with 83.6%.
        # Christine Drazan (R, the 2022 nominee) won the Republican primary
        # with 40.5% -- a rematch of 2022, Oregon's first since 1978. No
        # Betsy-Johnson-caliber independent this cycle: the two minor
        # independents who filed (Ziwahatan, Duke) have no legislative
        # experience, meaningful fundraising, or general-election polling,
        # so unlike 2022 this is modeled as a straightforward 2-candidate race.
        "candidates": [
            {"name": "Christine Drazan", "party": "Republican", "incumbent": False},
            {"name": "Tina Kotek", "party": "Democratic", "incumbent": True},
        ],
        # A third poll (Hoffman Research Group, May 11-12) tested Kotek vs.
        # Chris Dudley, who did NOT win the GOP primary -- excluded as not
        # the real matchup rather than reused.
        "raw_polls": [
            {
                "pollster": "FM3 Research",
                "sponsor": None,
                "field_start_date": "2026-01-28",
                "field_end_date": "2026-02-04",
                "release_date": "2026-02-07",
                "sample_size": 1065,
                "population": "LV",
                "margin_of_error": 3.1,
                "undecided_pct": 15.0,
                "source_url": OR_WIKI_SOURCE,
                "results": {"Christine Drazan": 40.0, "Tina Kotek": 45.0},
            },
            {
                "pollster": "Public Opinion Strategies",
                "sponsor": "Republican",
                "field_start_date": "2026-06-22",
                "field_end_date": "2026-06-24",
                "release_date": "2026-07-10",
                "sample_size": 600,
                "population": "RV",
                "margin_of_error": 4.0,
                "undecided_pct": 8.0,
                "source_url": "https://www.newsweek.com/christine-drazan-tina-kotek-oregon-governor-race-poll-11972614",
                "results": {"Christine Drazan": 48.0, "Tina Kotek": 44.0},
            },
        ],
    },
    "mi": {
        "state_name": "Michigan",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Michigan_gubernatorial_election",
        # Open seat: Whitmer (D) is term-limited. Michigan's primary is
        # August 4, 2026 -- NOT settled as of this writing. Modeled with
        # named presumptive nominees rather than deferred: Jocelyn Benson
        # (D, Secretary of State) faces only token primary opposition and
        # is treated as settled, matching how Florida's Jolly was handled.
        # John James (R, Trump-endorsed June 22, 2026) is used as the GOP
        # proxy, but this side is genuinely less certain -- Mike Cox and
        # Perry Johnson remain active candidates with real double-digit
        # support as of early July, and could still win the primary
        # instead. Independent Mike Duggan (Detroit mayor) ran a serious
        # 3-way campaign but withdrew May 22, 2026; polls before that date
        # tested a real 3-way race, so Duggan's share (and any other/
        # undecided) is folded into undecided_pct the same way third-party
        # shares are handled elsewhere in this dataset, rather than treating
        # those as clean 2-way polls.
        "candidates": [
            {"name": "John James", "party": "Republican", "incumbent": False},
            {"name": "Jocelyn Benson", "party": "Democratic", "incumbent": False},
        ],
        # A June 11-13, 2026 Mitchell/MIRS poll was excluded: two secondary
        # sources reported contradictory toplines for it (Benson+11 vs.
        # James+6) and the original release couldn't be directly verified.
        "raw_polls": [
            {
                "pollster": "Mitchell Research (MIRS)",
                "sponsor": None,
                "field_start_date": "2025-11-12",
                "field_end_date": "2025-11-12",
                "release_date": "2025-12-02",
                "sample_size": 616,
                "population": "LV",
                "margin_of_error": 3.7,
                "undecided_pct": 32.0,
                "source_url": "https://michiganadvance.com/2025/12/02/rogers-leads-senate-poll-as-stevens-closes-gap-benson-james-top-early-2026-governor-field/",
                "results": {"John James": 37.0, "Jocelyn Benson": 31.0},
            },
            {
                "pollster": "Glengariff Group",
                "sponsor": None,
                "field_start_date": "2026-01-27",
                "field_end_date": "2026-02-02",
                "release_date": "2026-02-05",
                "sample_size": 600,
                "population": "RV",
                "margin_of_error": 4.0,
                "undecided_pct": 43.9,
                "source_url": "https://www.detroitchamber.com/new-poll-shows-jocelyn-benson-leading-michigan-governor-race/",
                "results": {"John James": 28.3, "Jocelyn Benson": 27.8},
            },
            {
                "pollster": "Impact Research",
                "sponsor": "Democratic",
                "field_start_date": "2026-02-09",
                "field_end_date": "2026-02-16",
                "release_date": "2026-02-19",
                "sample_size": 800,
                "population": "LV",
                "margin_of_error": 3.5,
                "undecided_pct": 25.0,
                "source_url": "https://www.newsweek.com/democrat-gop-michigan-governor-race-polls-charts-jocelyn-benson-john-james-11955474",
                "results": {"John James": 36.0, "Jocelyn Benson": 39.0},
            },
            {
                "pollster": "Glengariff Group",
                "sponsor": None,
                "field_start_date": "2026-04-28",
                "field_end_date": "2026-05-01",
                "release_date": "2026-05-04",
                "sample_size": 600,
                "population": "LV",
                "margin_of_error": 4.0,
                "undecided_pct": 36.6,
                "source_url": "https://www.detroitchamber.com/new-poll-shows-jocelyn-benson-leading-michigan-governor-race/",
                "results": {"John James": 29.2, "Jocelyn Benson": 34.2},
            },
            {
                "pollster": "Mitchell Research (MIRS)",
                "sponsor": None,
                "field_start_date": "2026-05-01",
                "field_end_date": "2026-05-07",
                "release_date": "2026-05-12",
                "sample_size": 607,
                "population": "LV",
                "margin_of_error": 6.0,
                "undecided_pct": 28.0,
                "source_url": "https://www.detroitnews.com/story/news/politics/2026/05/12/michigan-governor-latest-poll-jocelyn-benson-mike-duggan-john-james-perry-johnson/90043032007/",
                "results": {"John James": 30.0, "Jocelyn Benson": 42.0},
            },
            {
                "pollster": "TIPP Insights",
                "sponsor": None,
                "field_start_date": "2026-05-20",
                "field_end_date": "2026-05-23",
                "release_date": "2026-05-26",
                "sample_size": 1163,
                "population": "LV",
                "margin_of_error": 3.0,
                "undecided_pct": 13.0,
                "source_url": "https://www.newsweek.com/republican-chances-of-beating-benson-to-flip-michigan-as-duggan-exits-race-11979456",
                "results": {"John James": 38.0, "Jocelyn Benson": 49.0},
            },
        ],
    },
    "ne": {
        "state_name": "Nebraska",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Nebraska_gubernatorial_election",
        # Incumbent Jim Pillen (R) won his May 12, 2026 primary with 75.4%
        # over 5 minor GOP rivals. Former state Sen. Lynne Walz (D) won her
        # primary with 91.5% over Larry Marvin. Both nominations are settled.
        # A Legal Marijuana NOW candidate, Rick Beard, also qualified for the
        # general ballot; his share is folded into undecided_pct in the two
        # polls below, the same convention used for other minor candidates
        # throughout this dataset (e.g. MI's Duggan, ME's Bennett).
        "candidates": [
            {"name": "Jim Pillen", "party": "Republican", "incumbent": True},
            {"name": "Lynne Walz", "party": "Democratic", "incumbent": False},
        ],
        # Only 2 real, independently verifiable general-election trial-heat
        # polls were located, both commissioned by the Walz campaign (so both
        # carry an inherent house-effect caveat, same as OH's Democratic-
        # sponsored polls elsewhere in this dataset) but reported on by
        # independent outlets with real toplines/dates/samples. Two earlier
        # polls in the same Lake Research Partners tracking series (widely
        # reported as "Pillen +12" in July 2025 and "Pillen +4" in December
        # 2025) are excluded here: coverage of both only gives a month, not
        # field start/end dates, and no sample size/MoE was found for either
        # -- not enough to seed a poll record with the same rigor as the two
        # below, rather than fabricating placeholder dates.
        "raw_polls": [
            {
                "pollster": "Public Policy Polling",
                "sponsor": "Democratic",
                "field_start_date": "2026-04-06",
                "field_end_date": "2026-04-07",
                "release_date": "2026-04-14",
                "sample_size": 670,
                "population": "RV",
                "margin_of_error": 3.8,
                "undecided_pct": 29.0,
                "source_url": "https://nebraskaexaminer.com/2026/04/14/walz-campaign-says-new-poll-shows-pillens-vulnerability/",
                "results": {"Jim Pillen": 38.0, "Lynne Walz": 33.0},
            },
            {
                "pollster": "Lake Research Partners",
                "sponsor": "Democratic",
                "field_start_date": "2026-04-25",
                "field_end_date": "2026-04-29",
                "release_date": "2026-05-03",
                "sample_size": 900,
                "population": "LV",
                "margin_of_error": 3.3,
                "undecided_pct": 8.0,
                "source_url": "https://nebraskapublicmedia.org/en/news/news-articles/internal-poll-shows-democratic-challenger-lynne-walz-closing-in-on-jim-pillen-in-governors-race/",
                "results": {"Jim Pillen": 47.0, "Lynne Walz": 45.0},
            },
        ],
    },
    "ks": {
        "state_name": "Kansas",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Kansas_gubernatorial_election",
        # Gov. Laura Kelly (D) is term-limited (2-consecutive-term max) and
        # cannot run again -- this is an open seat. Neither party's Aug 4,
        # 2026 primary is decided: GOP frontrunner is state Senate President
        # Ty Masterson, with Secretary of State Scott Schwab and Insurance
        # Commissioner Vicki Schmidt also running; Democrats have a real
        # primary between state Sens. Cindy Holscher and Ethan Corson and
        # Overland Park Mayor Curt Skoog. Per explicit direction, no
        # presumptive nominee is named here -- this race uses generic party
        # placeholders and is fundamentals-only. No true generic-ballot
        # ("generic Republican" vs. "generic Democrat") general-election poll
        # was found. The only public poll located (Change Research/Capitol
        # Bee, June 2026) tested named candidates within the Democratic
        # primary only, which isn't usable for a general-election forecast.
        "candidates": [
            {"name": "Republican Nominee", "party": "Republican", "incumbent": False},
            {"name": "Democratic Nominee", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [],
    },
    "az": {
        "state_name": "Arizona",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_Arizona_gubernatorial_election",
        # Gov. Katie Hobbs (D) is running for reelection and is functionally
        # unopposed in the Democratic primary -- treated as the settled
        # nominee. The GOP primary (July 21, 2026) is NOT settled: Rep. Andy
        # Biggs is the clear frontrunner, Rep. David Schweikert is also
        # running, and Karrin Taylor Robson (an earlier Trump-endorsed
        # candidate) withdrew Feb. 12, 2026. Per explicit direction, the
        # Republican side is a generic "TBD" placeholder rather than naming
        # a presumptive nominee.
        #
        # Every general-election trial-heat poll found tests Hobbs against a
        # SPECIFIC named Republican (Biggs, Schweikert, and, before her
        # withdrawal, Robson) rather than a true generic-ballot question. Per
        # explicit direction to aggregate across contenders, each poll below
        # represents one real polling wave (one pollster + field-date window)
        # averaged across every named-Republican matchup that wave tested --
        # e.g. Emerson's Nov 2025 release tested Biggs, Robson, AND
        # Schweikert as three separate matchups; the entry below is the
        # unweighted average of Hobbs's share, the Republican's share, and
        # undecided across those three. This keeps one poll record per real
        # release (matching how the pipeline dedupes on pollster + field
        # dates) while still reflecting every contender actually polled.
        "candidates": [
            {"name": "Katie Hobbs", "party": "Democratic", "incumbent": True},
            {"name": "Republican Nominee (TBD)", "party": "Republican", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Emerson College Polling",
                "sponsor": None,
                "field_start_date": "2025-11-08",
                "field_end_date": "2025-11-10",
                "release_date": "2025-11-14",
                "sample_size": 850,
                "population": "RV",
                "margin_of_error": 3.3,
                "undecided_pct": 15.0,
                "source_url": "https://emersoncollegepolling.com/arizona-2026-governor/",
                # Average of 3 named matchups: Hobbs 44/Biggs 43 (13% undec.),
                # Hobbs 43/Robson 42 (15% undec.), Hobbs 44/Schweikert 39
                # (16% undec.).
                "results": {"Katie Hobbs": 43.7, "Republican Nominee (TBD)": 41.3},
            },
            {
                "pollster": "Noble Predictive Insights",
                "sponsor": None,
                "field_start_date": "2026-02-23",
                "field_end_date": "2026-02-26",
                "release_date": "2026-03-04",
                "sample_size": 1023,
                "population": "RV",
                "margin_of_error": 3.06,
                "undecided_pct": 21.0,
                "source_url": "https://www.noblepredictiveinsights.com/post/azgov-biggs-benefits-from-field-consolidation-hobbs-holds-early-edge",
                # Average of 2 named matchups: Hobbs 42/Biggs 37 and Hobbs
                # 44/Schweikert 35 (~21% undecided each, per Newsweek's
                # independent write-up of the same release).
                "results": {"Katie Hobbs": 43.0, "Republican Nominee (TBD)": 36.0},
            },
            {
                "pollster": "Noble Predictive Insights",
                "sponsor": None,
                "field_start_date": "2026-05-05",
                "field_end_date": "2026-05-07",
                "release_date": "2026-05-18",
                "sample_size": 996,
                "population": "RV",
                "margin_of_error": 3.1,
                "undecided_pct": 22.5,
                "source_url": "https://www.noblepredictiveinsights.com/post/azgov-biggs-nears-majority-as-hobbs-holds-early-edge",
                # Average of 2 named matchups: Hobbs 41/Biggs 37 (includes a
                # separately-polled No Labels independent, Hugh Lytle, at 5%,
                # folded into undecided per this dataset's minor-candidate
                # convention) and Hobbs 42/Schweikert 35.
                "results": {"Katie Hobbs": 41.5, "Republican Nominee (TBD)": 36.0},
            },
        ],
    },
    "nh": {
        "state_name": "New Hampshire",
        "office": "Governor",
        "election_date": "2026-11-03",
        "wikipedia_page_title": "2026_New_Hampshire_gubernatorial_election",
        # Gov. Kelly Ayotte (R, elected 2024) is running for reelection with
        # no serious primary challenger. Cinde Warmington (D) -- an NH
        # Executive Councilor 2021-2025 who lost the 2024 Dem primary to
        # Joyce Craig -- announced Feb 18, 2026 and is described by the
        # Concord Monitor (June 12, 2026) as the "de-facto Democratic
        # nominee," with no other funded Democrat found on the primary
        # ballot. NH's primary is Sept. 8, 2026.
        "candidates": [
            {"name": "Kelly Ayotte", "party": "Republican", "incumbent": True},
            {"name": "Cinde Warmington", "party": "Democratic", "incumbent": False},
        ],
        "raw_polls": [
            {
                "pollster": "Saint Anselm College Survey Center",
                "sponsor": None,
                "field_start_date": "2026-03-16",
                "field_end_date": "2026-03-18",
                "release_date": "2026-03-24",
                "sample_size": 1491,
                "population": "RV",
                "margin_of_error": 2.5,
                "undecided_pct": 15.0,
                "source_url": "https://www.anselm.edu/sites/default/files/2026-03/March%202026%20NHRV%20Final_0.pdf",
                "results": {"Kelly Ayotte": 46.0, "Cinde Warmington": 39.0},
            },
            {
                "pollster": "UNH Survey Center",
                "sponsor": None,
                "field_start_date": "2026-04-17",
                "field_end_date": "2026-04-21",
                "release_date": "2026-04-23",
                "sample_size": 1295,
                "population": "LV",
                "margin_of_error": 2.9,
                # Boston Globe reported Ayotte 47 / Warmington 39 / undecided
                # 10 / other 4 -- the 4% "other" is folded into undecided_pct
                # per this dataset's minor-candidate convention.
                "undecided_pct": 14.0,
                "source_url": "https://www.bostonglobe.com/2026/04/24/metro/unh-survey-governor-ayotte-warmington/",
                "results": {"Kelly Ayotte": 47.0, "Cinde Warmington": 39.0},
            },
            {
                "pollster": "UNH Survey Center",
                "sponsor": None,
                "field_start_date": "2026-06-18",
                "field_end_date": "2026-06-23",
                "release_date": "2026-07-01",
                "sample_size": 2396,
                "population": "LV",
                "margin_of_error": 2.0,
                "undecided_pct": 17.0,
                "source_url": "https://www.nhpr.org/politics/2026-07-01/unh-poll-shows-tight-races-for-governor-and-u-s-senate-2026-midterms",
                "results": {"Kelly Ayotte": 44.0, "Cinde Warmington": 39.0},
            },
        ],
    },
}
