"""Uses a real captured HTML snippet from PollingSource.com's /pollsters
table (fetched 2026-07-15)."""

from unittest.mock import patch

import httpx

from app.ingestion.pollster_ratings_scraper import (
    _parse_error_pts,
    _parse_int,
    _parse_lean,
    _parse_pct,
    fetch_pollster_ratings,
)

RATINGS_TABLE_HTML = """
<table>
<tbody>
<tr>
<th>Pollster</th>
<th title="All scored general-election polls, 2014 to present">Polls</th>
<th title="Election cycles the firm was scored in">Cycles</th>
<th title="Mean absolute error of the poll margin vs the certified margin">Avg. Error</th>
<th title="Direction of the average miss (D-vs-R polls only)">Lean</th>
<th title="Share of scored polls whose leader won">Winner Called</th>
</tr>
<tr>
<td><a href="/pollsters/yougov">YouGov</a></td>
<td>443</td>
<td>7</td>
<td>5.2 pts</td>
<td>D+3.4</td>
<td>82%</td>
</tr>
<tr>
<td><a href="/pollsters/emerson-college">Emerson College</a></td>
<td>417</td>
<td>8</td>
<td>4.3 pts</td>
<td>D+0.7</td>
<td>77%</td>
</tr>
<tr>
<td><a href="/pollsters/trafalgar-group">Trafalgar Group</a></td>
<td>192</td>
<td>8</td>
<td>3.6 pts</td>
<td>R+2.0</td>
<td>72%</td>
</tr>
</tbody>
</table>
"""

FULL_PAGE_HTML = f"<html><body>{RATINGS_TABLE_HTML}</body></html>"


def _mock_response(html: str) -> httpx.Response:
    return httpx.Response(200, text=html, request=httpx.Request("GET", "https://pollingsource.com/pollsters"))


def test_fetch_pollster_ratings_parses_every_row():
    with patch("httpx.get", return_value=_mock_response(FULL_PAGE_HTML)):
        ratings = fetch_pollster_ratings()

    assert len(ratings) == 3
    by_name = {r.pollster: r for r in ratings}

    yougov = by_name["YouGov"]
    assert yougov.avg_error_pts == 5.2
    assert yougov.lean_party == "Democratic"
    assert yougov.lean_pts == 3.4
    assert yougov.winner_called_pct == 82.0
    assert yougov.polls_count == 443
    assert yougov.cycles_count == 7
    assert yougov.source_url == "https://pollingsource.com/pollsters"

    trafalgar = by_name["Trafalgar Group"]
    assert trafalgar.lean_party == "Republican"
    assert trafalgar.lean_pts == 2.0


def test_fetch_pollster_ratings_returns_empty_list_on_network_failure():
    with patch("httpx.get", side_effect=httpx.ConnectError("boom")):
        assert fetch_pollster_ratings() == []


def test_fetch_pollster_ratings_returns_empty_list_when_table_missing():
    with patch(
        "httpx.get",
        return_value=_mock_response("<html><body><p>no tables here</p></body></html>"),
    ):
        assert fetch_pollster_ratings() == []


def test_fetch_pollster_ratings_returns_empty_list_on_http_error_status():
    request = httpx.Request("GET", "https://pollingsource.com/pollsters")
    with patch("httpx.get", return_value=httpx.Response(403, text="Forbidden", request=request)):
        assert fetch_pollster_ratings() == []


def test_parse_error_pts_extracts_the_number():
    assert _parse_error_pts("5.2 pts") == 5.2
    assert _parse_error_pts("—") is None


def test_parse_pct_extracts_the_number():
    assert _parse_pct("82%") == 82.0
    assert _parse_pct("—") is None


def test_parse_int_handles_non_numeric_placeholder():
    assert _parse_int("443") == 443
    assert _parse_int("—") is None


def test_parse_lean_handles_democratic_republican_and_even():
    assert _parse_lean("D+3.4") == ("Democratic", 3.4)
    assert _parse_lean("R+2.0") == ("Republican", 2.0)
    assert _parse_lean("EVEN") == (None, 0.0)
    assert _parse_lean("garbage") == (None, None)
