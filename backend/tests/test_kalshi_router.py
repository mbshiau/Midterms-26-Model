from datetime import datetime, timezone

from app.models import Candidate, MarketOdds


def test_kalshi_odds_is_empty_for_a_race_with_no_configured_ticker(client):
    resp = client.get("/races/pa-gov/kalshi")
    assert resp.status_code == 200
    assert resp.json() == []


def test_kalshi_odds_is_empty_when_a_ticker_is_configured_but_never_scraped(client):
    # California's seed data has kalshi_ticker set, but nothing populates
    # MarketOdds until a real scrape succeeds -- a freshly-seeded DB has
    # none yet.
    resp = client.get("/races/ca-gov/kalshi")
    assert resp.status_code == 200
    assert resp.json() == []


def test_kalshi_odds_returns_a_populated_market(client, db_session):
    candidate = db_session.query(Candidate).filter(Candidate.name == "Xavier Becerra").first()
    db_session.add(
        MarketOdds(
            candidate_id=candidate.id,
            ticker="KXGOVCA-26-XBEC",
            yes_price_pct=93.4,
            as_of=datetime(2026, 7, 13, tzinfo=timezone.utc),
            source_url="https://kalshi.com/markets/kxgovca-26-xbec",
        )
    )
    db_session.commit()

    resp = client.get("/races/ca-gov/kalshi")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["candidate"]["name"] == "Xavier Becerra"
    assert body[0]["ticker"] == "KXGOVCA-26-XBEC"
    assert body[0]["win_probability_pct"] == 93.4
    assert body[0]["source_url"] == "https://kalshi.com/markets/kxgovca-26-xbec"


def test_kalshi_odds_404s_for_an_unknown_state(client):
    resp = client.get("/races/zz-gov/kalshi")
    assert resp.status_code == 404


def test_kalshi_odds_is_not_present_in_the_forecast_response(client):
    # Regression guard: Kalshi must stay out of the model's own output --
    # this is a standalone section now, not a blend input.
    forecast = client.get("/races/pa-gov/forecast").json()
    assert "n_markets_used" not in forecast
    assert "kalshi_weight_pct" not in forecast
    for result in forecast["results"]:
        assert "kalshi_vote_share" not in result
