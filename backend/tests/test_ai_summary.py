from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.database import Base
from app.models import Candidate, ForecastResult, ForecastSnapshot, MarketOdds, NewsArticle, Race
from app.services.ai_summary import (
    generate_article_relevance,
    generate_market_analysis,
    get_race_intelligence,
    update_race_intelligence,
)


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture()
def race_with_candidates(db_session, tables):
    race = Race(
        state_code="zz",
        state_name="Test State",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="Test",
    )
    db_session.add(race)
    db_session.flush()
    dem = Candidate(race_id=race.id, name="Dem Candidate", party="Democratic")
    rep = Candidate(race_id=race.id, name="Rep Candidate", party="Republican")
    db_session.add_all([dem, rep])
    db_session.commit()
    db_session.refresh(dem)
    db_session.refresh(rep)
    return race, dem, rep


def _article(race_id: int, n: int) -> NewsArticle:
    return NewsArticle(
        race_id=race_id,
        headline=f"Headline {n}",
        source="Example News",
        url=f"https://example.com/{n}",
        published_at=datetime.now(timezone.utc),
    )


def _fake_ai_client(text: str | None = "A generated summary.", raises: bool = False) -> MagicMock:
    client = MagicMock()
    if raises:
        client.chat.completions.create.side_effect = RuntimeError("AI provider is down")
    else:
        choice = MagicMock()
        choice.message.content = text
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response
    return client


def test_generate_article_relevance_returns_none_when_ai_provider_not_configured(monkeypatch, race_with_candidates):
    monkeypatch.setattr(settings, "uf_navigator_api_key", "")
    race, _, _ = race_with_candidates
    assert generate_article_relevance(race, _article(race.id, 1)) is None


def test_generate_article_relevance_returns_generated_text(monkeypatch, race_with_candidates):
    monkeypatch.setattr(settings, "uf_navigator_api_key", "test-key")
    race, _, _ = race_with_candidates
    article = _article(race.id, 1)

    with patch(
        "app.services.ai_summary._client",
        return_value=_fake_ai_client("This signals renewed momentum for one campaign."),
    ):
        result = generate_article_relevance(race, article)

    assert result == "This signals renewed momentum for one campaign."


def test_generate_article_relevance_returns_none_on_ai_provider_failure(monkeypatch, race_with_candidates):
    monkeypatch.setattr(settings, "uf_navigator_api_key", "test-key")
    race, _, _ = race_with_candidates
    article = _article(race.id, 1)

    with patch("app.services.ai_summary._client", return_value=_fake_ai_client(raises=True)):
        assert generate_article_relevance(race, article) is None


def test_generate_market_analysis_returns_none_without_forecast_or_kalshi(race_with_candidates):
    race, dem, rep = race_with_candidates
    assert generate_market_analysis(race, None, [], {dem.id: dem, rep.id: rep}) is None


def test_generate_market_analysis_returns_generated_text(monkeypatch, db_session, race_with_candidates):
    monkeypatch.setattr(settings, "uf_navigator_api_key", "test-key")
    race, dem, rep = race_with_candidates

    snapshot = ForecastSnapshot(race_id=race.id, n_simulations=1000, n_polls_used=5, poll_weight_alpha=0.5)
    db_session.add(snapshot)
    db_session.flush()
    db_session.add(
        ForecastResult(
            snapshot_id=snapshot.id,
            candidate_id=dem.id,
            mean_vote_share=52.0,
            median_vote_share=52.0,
            std_dev=3.0,
            win_probability=0.70,  # ForecastResult.win_probability is a 0-1 fraction, not 0-100
            ci_low=46.0,
            ci_high=58.0,
            polling_vote_share=52.0,
            fundamentals_vote_share=52.0,
        )
    )
    db_session.commit()

    kalshi_row = MarketOdds(
        candidate_id=dem.id,
        ticker="KXTEST-26-DEM",
        yes_price_pct=80.0,
        as_of=datetime.now(timezone.utc),
        source_url="https://kalshi.com/markets/kxtest-26-dem",
    )

    with patch(
        "app.services.ai_summary._client",
        return_value=_fake_ai_client("Markets are more bullish than the model."),
    ):
        result = generate_market_analysis(race, snapshot, [kalshi_row], {dem.id: dem, rep.id: rep})

    assert result == "Markets are more bullish than the model."


def test_update_race_intelligence_creates_then_upserts_in_place(db_session, race_with_candidates):
    race, _, _ = race_with_candidates

    first = update_race_intelligence(db_session, race.id, None)
    assert first.market_analysis is None

    second = update_race_intelligence(db_session, race.id, "Analysis one.")
    assert second.id == first.id  # upserted in place, not accumulated
    assert second.market_analysis == "Analysis one."

    all_rows = db_session.query(type(second)).all()
    assert len(all_rows) == 1


def test_update_race_intelligence_preserves_previous_value_when_new_analysis_is_none(db_session, race_with_candidates):
    race, _, _ = race_with_candidates
    update_race_intelligence(db_session, race.id, "Kept analysis.")

    # A transient AI-provider failure (None) must not blank out a previously
    # cached value -- it should just leave it as-is until the next success.
    row = update_race_intelligence(db_session, race.id, None)

    assert row.market_analysis == "Kept analysis."


def test_get_race_intelligence_returns_none_when_no_row_exists(db_session, race_with_candidates):
    race, _, _ = race_with_candidates
    assert get_race_intelligence(db_session, race.id) is None
