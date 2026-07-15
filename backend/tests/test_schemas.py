from datetime import date

from app.schemas import FundamentalsBreakdownOut

# A real production incident: adding generic_ballot_* as required fields on
# FundamentalsBreakdownOut broke every existing forecast snapshot, whose
# stored fundamentals_breakdown JSON predates this feature and simply has no
# such keys at all -- every /forecast and /forecast/history response 500'd.
OLD_STYLE_BREAKDOWN = {
    "gubernatorial_lean_pts": 1.0,
    "senate_lean_pts": 2.0,
    "presidential_lean_pts": 3.0,
    "combined_historical_lean_pts": 4.0,
    "incumbency_pts": 5.0,
    "registration_trend_pts": 6.0,
    "national_environment_pts": 7.0,
    "total_dem_margin_pts": 8.0,
    "president_name": "Donald Trump",
    "president_approval_pct": 37.0,
    "president_approval_as_of": date(2026, 7, 10),
    "president_approval_source_url": "https://example.com",
    "gubernatorial_elections_count": 3,
    "senate_elections_count": 3,
    "presidential_elections_count": 3,
    # generic_ballot_* deliberately absent, as in any snapshot generated
    # before this feature existed.
}


def test_fundamentals_breakdown_out_accepts_pre_generic_ballot_snapshots():
    parsed = FundamentalsBreakdownOut(**OLD_STYLE_BREAKDOWN)
    assert parsed.generic_ballot_dem_pct is None
    assert parsed.generic_ballot_rep_pct is None
    assert parsed.generic_ballot_as_of is None
    assert parsed.generic_ballot_source_url is None


def test_fundamentals_breakdown_out_accepts_a_populated_generic_ballot():
    parsed = FundamentalsBreakdownOut(
        **OLD_STYLE_BREAKDOWN,
        generic_ballot_dem_pct=47.8,
        generic_ballot_rep_pct=42.0,
        generic_ballot_as_of=date(2026, 7, 10),
        generic_ballot_source_url="https://example.com/ballot",
    )
    assert parsed.generic_ballot_dem_pct == 47.8
