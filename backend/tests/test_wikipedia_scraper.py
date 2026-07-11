"""Parser tests use real captured HTML snippets from Wikipedia (fetched
2026-07-10) rather than live network calls, so they run offline and don't
break if the article structure changes tomorrow."""

from datetime import date
from unittest.mock import patch

from bs4 import BeautifulSoup

from app.ingestion.wikipedia_scraper import (
    _clean_pollster_name,
    _find_polling_table,
    _parse_date_range,
    _parse_moe,
    _parse_pct,
    _parse_sample,
    fetch_general_election_polls,
)

# Real markup captured from en.wikipedia.org/wiki/2026_Pennsylvania_gubernatorial_election,
# "General election > Polling" section, trimmed to a header + 3 rows.
POLLING_TABLE_HTML = """
<table class="wikitable sortable" style="text-align:center;font-size:90%;line-height:17px">
<tbody><tr valign="bottom">
<th>Poll source</th>
<th>Date(s)<br />administered</th>
<th>Sample<br />size</th>
<th>Margin<br />of error</th>
<th style="width:100px;">Josh<br />Shapiro (D)</th>
<th style="width:100px;">Stacy<br />Garrity (R)</th>
<th>Other</th>
<th>Undecided</th></tr>
<tr>
<td style="text-align:left;">PennLive<sup id="cite_ref-5" class="reference"><a href="#cite_note-5">[3]</a></sup>
</td>
<td>June 18&#8211;25, 2026</td>
<td>644 (RV)</td>
<td>&#177; 4.14%</td>
<td style="color:black;background-color:#B0CEFF"><b>54%</b></td>
<td>29%</td>
<td>7%</td>
<td>9%</td></tr>
<tr>
<td style="text-align:left;"><a href="/wiki/Franklin_%26_Marshall_College">Franklin &amp; Marshall College</a><sup id="cite_ref-8" class="reference"><a href="#cite_note-8">[4]</a></sup>
</td>
<td>June 8&#8211;14, 2026</td>
<td>546 (RV)</td>
<td>&#177; 5.1%</td>
<td style="color:black;background-color:#B0CEFF"><b>50%</b></td>
<td>28%</td>
<td>6%</td>
<td>16%</td></tr>
<tr>
<td style="text-align:left;"><a href="/wiki/Susquehanna_Polling_%26_Research">Susquehanna Polling &amp; Research</a> (R)<sup id="cite_ref-13" class="reference"><a href="#cite_note-13">[7]</a></sup>
</td>
<td>February 18 &#8211; March 1, 2026</td>
<td>834 (RV)</td>
<td>&#177; 4.1%</td>
<td style="color:black;background-color:#B0CEFF"><b>48%</b></td>
<td>28%</td>
<td>&#8211;</td>
<td>17%</td></tr>
</tbody></table>
"""

FULL_PAGE_HTML = f"<html><body>{POLLING_TABLE_HTML}</body></html>"


def test_parse_date_range_same_month():
    assert _parse_date_range("June 18–25, 2026", 2026) == (date(2026, 6, 18), date(2026, 6, 25))


def test_parse_date_range_cross_month():
    assert _parse_date_range("February 18 – March 1, 2026", 2026) == (
        date(2026, 2, 18),
        date(2026, 3, 1),
    )


def test_parse_sample_extracts_size_and_population():
    assert _parse_sample("644 (RV)") == (644, "RV")
    assert _parse_sample("1,579 (RV)") == (1579, "RV")


def test_parse_moe_strips_symbol():
    assert _parse_moe("± 4.14%") == 4.14


def test_parse_pct_handles_dash_as_zero():
    assert _parse_pct("28%") == 28.0
    assert _parse_pct("–") == 0.0


def test_clean_pollster_name_strips_footnotes_and_partisan_tag():
    soup = BeautifulSoup(
        '<td><a href="/wiki/X">Susquehanna Polling &amp; Research</a> (R)'
        '<sup class="reference">[7]</sup></td>',
        "html.parser",
    )
    assert _clean_pollster_name(soup.td) == "Susquehanna Polling & Research"


def test_find_polling_table_matches_on_candidate_surnames():
    soup = BeautifulSoup(FULL_PAGE_HTML, "html.parser")
    table = _find_polling_table(soup, ["Shapiro", "Garrity"])
    assert table is not None

    no_match = _find_polling_table(soup, ["Mastriano", "SomeoneElse"])
    assert no_match is None


def test_fetch_general_election_polls_end_to_end():
    with patch(
        "app.ingestion.wikipedia_scraper.fetch_wikipedia_html", return_value=FULL_PAGE_HTML
    ):
        polls = fetch_general_election_polls(
            "2026_Pennsylvania_gubernatorial_election",
            {"Shapiro": "Josh Shapiro", "Garrity": "Stacy Garrity"},
        )

    assert len(polls) == 3

    pennlive = next(p for p in polls if p.pollster == "PennLive")
    assert pennlive.field_start_date == date(2026, 6, 18)
    assert pennlive.field_end_date == date(2026, 6, 25)
    assert pennlive.sample_size == 644
    assert pennlive.population == "RV"
    assert pennlive.margin_of_error == 4.14
    assert pennlive.results == {"Josh Shapiro": 54.0, "Stacy Garrity": 29.0}
    assert pennlive.undecided_pct == 16.0  # 7% other + 9% undecided
    assert pennlive.source_url.endswith("2026_Pennsylvania_gubernatorial_election")

    susquehanna = next(p for p in polls if "Susquehanna" in p.pollster)
    assert susquehanna.pollster == "Susquehanna Polling & Research"  # "(R)" stripped
    assert susquehanna.field_start_date == date(2026, 2, 18)
    assert susquehanna.field_end_date == date(2026, 3, 1)


def test_fetch_general_election_polls_returns_empty_on_network_failure():
    with patch("app.ingestion.wikipedia_scraper.fetch_wikipedia_html", return_value=None):
        polls = fetch_general_election_polls(
            "2026_Pennsylvania_gubernatorial_election",
            {"Shapiro": "Josh Shapiro", "Garrity": "Stacy Garrity"},
        )
    assert polls == []
