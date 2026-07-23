"""AI-generated context for the Race Intelligence section: a model-vs-Kalshi
comparison and per-article relevance blurbs, both written by an LLM behind
an OpenAI-compatible chat completions API -- currently
UF Navigator (settings.uf_navigator_base_url/model), but any OpenAI-
compatible provider works by swapping those two settings.

Deliberately a separate, standalone integration from the Anthropic-powered
tooling used elsewhere for this project's own development -- this module is
the only place in the app that talks to an LLM at runtime, and the only
place that imports the openai SDK. Like every scraper in app.ingestion,
every call here returns None on any failure (missing API key, network
error, empty/malformed response) rather than raising -- an LLM outage must
never block a race's forecast from regenerating (see
app.ingestion.scheduler._run_forecast_refresh_job /
_run_market_intel_refresh_job).

Output is generated once per scheduled refresh and cached on
RaceIntelligence/NewsArticle (see update_race_intelligence,
app.ingestion.scheduler.refresh_race_intelligence) rather than called on
every page load, both for cost and so the "AI-generated ... as of <time>"
timestamp shown in the UI means something.
"""

import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Candidate, ForecastSnapshot, MarketOdds, NewsArticle, Race, RaceIntelligence

logger = logging.getLogger(__name__)

# Paces real calls so a scheduled refresh -- which can make dozens of calls
# across every race (up to ARTICLES_PER_RACE new-article relevance blurbs +
# 1 market analysis, per race) -- doesn't get rate-limited by the provider.
# Simple fixed-interval pace, not a token-bucket or
# backoff/retry scheme -- good enough for a background job with no user
# waiting on it, and steady-state volume is low anyway (see
# app.ingestion.scheduler.refresh_race_intelligence: article relevance is
# only regenerated for articles that don't have one cached yet). Configurable
# via settings.ai_min_seconds_between_calls (rather than a bare module
# constant) so tests can zero it out instead of sleeping for real.
_last_call_at: float | None = None


def _wait_for_rate_limit() -> None:
    global _last_call_at
    min_interval = settings.ai_min_seconds_between_calls
    if min_interval <= 0:
        return
    now = time.monotonic()
    if _last_call_at is not None:
        elapsed = now - _last_call_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
    _last_call_at = time.monotonic()


ARTICLE_RELEVANCE_SYSTEM_PROMPT = (
    "You are an election analyst. Given a single news headline about a race, write 1-2 "
    "plain-prose sentences: briefly state what the headline suggests happened, then explain "
    "why it's relevant to this race. Base this only on the headline, source, and date given -- "
    "you don't have the article body, so don't invent details or quotes it doesn't support. "
    "No bullet points, no headers."
)

MARKET_ANALYSIS_SYSTEM_PROMPT = (
    "You are an election analyst comparing a statistical polling-and-fundamentals model's "
    "win probability against a prediction market's implied probability for the same race. "
    "State whether the two roughly agree or diverge, and if they diverge, suggest one or two "
    "plausible, clearly-hedged reasons (e.g. traders pricing in expected future movement, "
    "market illiquidity, the model not yet reflecting a very recent event). Stay probabilistic "
    "and cautious -- never claim certainty about why markets and models differ, and never "
    "assert one is more correct than the other. Write 2-3 sentences, plain prose."
)


def _client():
    if not settings.uf_navigator_api_key:
        return None
    from openai import OpenAI  # local import: keeps this an optional dependency at import time

    return OpenAI(api_key=settings.uf_navigator_api_key, base_url=settings.uf_navigator_base_url)


def _generate(system_prompt: str, user_prompt: str) -> str | None:
    client = _client()
    if client is None:
        return None
    _wait_for_rate_limit()
    try:
        response = client.chat.completions.create(
            model=settings.uf_navigator_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception as e:
        logger.warning("AI generation failed: %s", e)
        return None


def generate_article_relevance(race: Race, article: NewsArticle) -> str | None:
    """1-2 sentence blurb for a single headline: what it suggests happened +
    why it matters to this race. Only the headline/source/date go into the
    prompt -- the RSS feed never gives us the article body (see
    app.ingestion.news_scraper), so this is a read of the headline itself,
    not the full article."""
    user_prompt = (
        f"Race: {race.state_name} {race.office}, {race.election_date.isoformat()}.\n\n"
        f"Headline: {article.headline} ({article.source}, {article.published_at.date().isoformat()})"
    )
    return _generate(ARTICLE_RELEVANCE_SYSTEM_PROMPT, user_prompt)


def generate_market_analysis(
    race: Race,
    forecast: ForecastSnapshot | None,
    kalshi_rows: list[MarketOdds],
    candidates_by_id: dict[int, Candidate],
) -> str | None:
    if forecast is None or not kalshi_rows:
        return None

    model_lines = "\n".join(
        # ForecastResult.win_probability is a 0-1 fraction (see
        # WinProbabilityHistoryChart.tsx's matching *100 on the frontend),
        # unlike MarketOdds.yes_price_pct below which is already 0-100.
        f"- {candidates_by_id[r.candidate_id].name} ({candidates_by_id[r.candidate_id].party}): "
        f"model win probability {r.win_probability * 100:.1f}%"
        for r in forecast.results
        if r.candidate_id in candidates_by_id
    )
    market_lines = "\n".join(
        f"- {candidates_by_id[row.candidate_id].name} ({candidates_by_id[row.candidate_id].party}): "
        f"Kalshi implied probability {row.yes_price_pct:.1f}%"
        for row in kalshi_rows
        if row.candidate_id in candidates_by_id
    )
    if not model_lines or not market_lines:
        return None

    user_prompt = (
        f"Race: {race.state_name} {race.office}, {race.election_date.isoformat()}.\n\n"
        f"Model forecast:\n{model_lines}\n\nKalshi prediction market:\n{market_lines}"
    )
    return _generate(MARKET_ANALYSIS_SYSTEM_PROMPT, user_prompt)


def update_race_intelligence(db: Session, race_id: int, market_analysis: str | None) -> RaceIntelligence:
    """Upserts the single current RaceIntelligence row for this race in
    place -- same convention as update_market_odds. A None market_analysis
    (AI provider unconfigured, no Kalshi data yet, or a transient failure)
    leaves the previously-cached value in place rather than clearing it, so
    the UI doesn't blank out until the next successful refresh."""
    row = db.query(RaceIntelligence).filter(RaceIntelligence.race_id == race_id).first()
    if row is None:
        row = RaceIntelligence(race_id=race_id)
        db.add(row)

    if market_analysis is not None:
        row.market_analysis = market_analysis
        row.market_analysis_generated_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    return row


def get_race_intelligence(db: Session, race_id: int) -> RaceIntelligence | None:
    return db.query(RaceIntelligence).filter(RaceIntelligence.race_id == race_id).first()
