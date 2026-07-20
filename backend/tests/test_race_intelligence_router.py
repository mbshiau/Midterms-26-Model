from datetime import datetime, timedelta, timezone

from app.models import Candidate, NewsArticle, RaceIntelligence


def test_intelligence_404s_for_an_unknown_state(client):
    resp = client.get("/races/zz-gov/intelligence")
    assert resp.status_code == 404


def test_intelligence_is_empty_shaped_for_a_freshly_seeded_race(client):
    # Startup deliberately never bootstraps Race Intelligence (see
    # app.main's lifespan) -- only the scheduled refresh populates it. A
    # fresh DB should return a well-shaped "nothing yet" response, not error.
    resp = client.get("/races/pa-gov/intelligence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["news_articles"] == []
    assert body["market_analysis"] is None


def test_intelligence_returns_cached_news_and_ai_text(client, db_session):
    race_id = db_session.query(Candidate).filter(Candidate.name == "Xavier Becerra").first().race_id
    db_session.add(
        NewsArticle(
            race_id=race_id,
            headline="Race heats up ahead of debate",
            source="Example News",
            url="https://example.com/a",
            published_at=datetime.now(timezone.utc),
            ai_relevance="This signals the campaigns are ramping up ahead of a key moment in the race.",
        )
    )
    db_session.add(
        RaceIntelligence(
            race_id=race_id,
            market_analysis="Markets and the model roughly agree on this race.",
        )
    )
    db_session.commit()

    resp = client.get("/races/ca-gov/intelligence")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["news_articles"]) == 1
    assert body["news_articles"][0]["headline"] == "Race heats up ahead of debate"
    assert body["news_articles"][0]["ai_relevance"] == (
        "This signals the campaigns are ramping up ahead of a key moment in the race."
    )
    assert body["market_analysis"] == "Markets and the model roughly agree on this race."


def test_intelligence_omits_articles_older_than_two_weeks(client, db_session):
    race_id = db_session.query(Candidate).filter(Candidate.name == "Xavier Becerra").first().race_id
    now = datetime.now(timezone.utc)
    db_session.add(
        NewsArticle(
            race_id=race_id,
            headline="Recent headline",
            source="Example News",
            url="https://example.com/recent",
            published_at=now - timedelta(days=3),
        )
    )
    db_session.add(
        NewsArticle(
            race_id=race_id,
            headline="Stale headline",
            source="Example News",
            url="https://example.com/stale",
            published_at=now - timedelta(days=20),
        )
    )
    db_session.commit()

    resp = client.get("/races/ca-gov/intelligence")
    headlines = {a["headline"] for a in resp.json()["news_articles"]}
    assert headlines == {"Recent headline"}


def test_intelligence_is_not_present_in_the_forecast_response(client):
    # Regression guard, mirroring the Kalshi one: Race Intelligence must stay
    # a standalone section, never blended into the model's own output.
    forecast = client.get("/races/pa-gov/forecast").json()
    assert "market_analysis" not in forecast
    for result in forecast["results"]:
        assert "news_vote_share" not in result
