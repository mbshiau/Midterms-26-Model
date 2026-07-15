"""Uses a real captured HTML snippet from Wikipedia's
2026_United_States_House_of_Representatives_elections "Opinion polling"
section (fetched 2026-07-15)."""

from datetime import date
from unittest.mock import patch

from app.ingestion.generic_ballot_scraper import fetch_current_generic_ballot

BALLOT_TABLE_HTML = """
<table class="wikitable sortable">
<tbody><tr>
<th>Source of pollaggregation</th>
<th>Dates administered</th>
<th>Dates updated</th>
<th>Republicans</th>
<th>Democrats</th>
<th>Other/Undecided</th>
<th>Margin</th></tr>
<tr>
<td>Decision Desk HQ</td>
<td>January 9, 2025 &#8211; July 10, 2026</td>
<td>July 10, 2026</td>
<td>40.5%</td>
<td>45.4%</td>
<td>14.1%</td>
<td>Democrats +4.9%</td></tr>
<tr>
<td>RealClearPolitics</td>
<td>June 7 &#8211; July 7, 2026</td>
<td>July 10, 2026</td>
<td>42.0%</td>
<td>48.2%</td>
<td>9.8%</td>
<td>Democrats +6.2%</td></tr>
<tr>
<td><b>Average</b></td>
<td>July 10, 2026</td>
<td>42.0%</td>
<td>47.8%</td>
<td>10.2%</td>
<td>Democrats +5.8%</td></tr>
</tbody></table>
"""

FULL_PAGE_HTML = f"<html><body>{BALLOT_TABLE_HTML}</body></html>"


def test_fetch_current_generic_ballot_reads_the_average_row():
    with patch(
        "app.ingestion.generic_ballot_scraper.fetch_wikipedia_html", return_value=FULL_PAGE_HTML
    ):
        result = fetch_current_generic_ballot()

    assert result is not None
    assert result.rep_pct == 42.0
    assert result.dem_pct == 47.8
    assert result.as_of == date(2026, 7, 10)
    assert result.source_url.endswith("2026_United_States_House_of_Representatives_elections")


def test_fetch_current_generic_ballot_returns_none_on_network_failure():
    with patch("app.ingestion.generic_ballot_scraper.fetch_wikipedia_html", return_value=None):
        assert fetch_current_generic_ballot() is None


def test_fetch_current_generic_ballot_returns_none_when_table_missing():
    with patch(
        "app.ingestion.generic_ballot_scraper.fetch_wikipedia_html",
        return_value="<html><body><p>no tables here</p></body></html>",
    ):
        assert fetch_current_generic_ballot() is None
