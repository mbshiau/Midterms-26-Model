"""Real, publicly reported topline polling for the 2026 PA governor race
(Shapiro D-incumbent vs Garrity R), compiled from the polling table at
en.wikipedia.org/wiki/2026_Pennsylvania_gubernatorial_election plus each
poll's own release where it could be located independently.

`undecided_pct` is the complement (100 - Shapiro% - Garrity%), folding in
any third-party/"other" share alongside true undecideds, since this schema
tracks only the two major-party candidates.

Release dates for polls where the exact release day wasn't confirmed in
source reporting (both F&M polls, and the PennLive/MAD Global Strategy
polls below) are reconstructed from field-close + that outlet's typical
turnaround (~2-5 days); sample size, MoE, and toplines are all as published.
The PennLive and MAD Global Strategy polls are sourced to the Wikipedia
polling table itself, since an independently reachable pollster press
release could not be located for them.
"""

CANDIDATES = [
    {"name": "Josh Shapiro", "party": "Democratic", "incumbent": True},
    {"name": "Stacy Garrity", "party": "Republican", "incumbent": False},
]

WIKI_SOURCE = "https://en.wikipedia.org/wiki/2026_Pennsylvania_gubernatorial_election"

RAW_POLLS = [
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
        "source_url": WIKI_SOURCE,
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
        "source_url": WIKI_SOURCE,
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
        "source_url": WIKI_SOURCE,
        "results": {"Josh Shapiro": 54.0, "Stacy Garrity": 29.0},
    },
]
