"""Uses a real captured HTML snippet from Wikipedia's
Opinion_polling_on_the_second_Trump_presidency page (fetched 2026-07-10)."""

from datetime import date
from unittest.mock import patch

from app.ingestion.approval_scraper import fetch_current_approval

APPROVAL_TABLE_HTML = """
<table class="wikitable sortable" style="text-align:center;line-height:0.96">
<tbody><tr>
<th>Aggregator</th>
<th>Updated</th>
<th>Approve</th>
<th>Disapprove</th>
<th>Unsure/Other</th>
<th>Lead</th></tr>
<tr>
<td><a href="https://ballotpedia.org/x">Ballotpedia</a></td>
<td>July 2, 2026</td>
<td>40.0%</td>
<td style="background:#8B8B54; color: white">58.0%</td>
<td>2.0%</td>
<td style="background:#8B8B54; color: white">&#8722;18.0%</td></tr>
<tr>
<td><a href="https://www.cnn.com/x">CNN</a></td>
<td>July 2, 2026</td>
<td>37.0%</td>
<td style="background:#8B8B54; color: white">62.0%</td>
<td>1.0%</td>
<td style="background:#8B8B54; color: white">&#8722;25.0%</td></tr>
<tr>
<td><b>Average</b></td>
<td>July 2, 2026</td>
<td>39.2%</td>
<td style="background:#8B8B54; color: white">57.7%</td>
<td>3.1%</td>
<td style="background:#8B8B54; color: white">&#8722;18.5%</td></tr>
</tbody></table>
"""

FULL_PAGE_HTML = f"<html><body>{APPROVAL_TABLE_HTML}</body></html>"


def test_fetch_current_approval_reads_the_average_row():
    with patch(
        "app.ingestion.approval_scraper.fetch_wikipedia_html", return_value=FULL_PAGE_HTML
    ):
        result = fetch_current_approval()

    assert result is not None
    assert result.approval_pct == 39.2
    assert result.disapproval_pct == 57.7
    assert result.as_of == date(2026, 7, 2)
    assert result.source_url.endswith("Opinion_polling_on_the_second_Trump_presidency")


def test_fetch_current_approval_returns_none_on_network_failure():
    with patch("app.ingestion.approval_scraper.fetch_wikipedia_html", return_value=None):
        assert fetch_current_approval() is None


def test_fetch_current_approval_returns_none_when_table_missing():
    with patch(
        "app.ingestion.approval_scraper.fetch_wikipedia_html",
        return_value="<html><body><p>no tables here</p></body></html>",
    ):
        assert fetch_current_approval() is None
