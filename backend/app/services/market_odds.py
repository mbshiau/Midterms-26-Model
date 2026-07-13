"""DB read/write helpers for the single current MarketOdds row per candidate
(same upsert-in-place convention as app.services.approval.PresidentApproval).

Kalshi prices are win *probabilities* (0-100). app.services.forecasting uses
that percentage directly as this candidate's Kalshi-implied vote share when
blending with polls/fundamentals -- a deliberate simplification (a market
price isn't literally a vote share) rather than converting it through an
assumed error model first.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ingestion.kalshi_scraper import ScrapedMarketOdds
from app.models import MarketOdds


def get_market_odds(db: Session, candidate_ids: list[int]) -> dict[int, MarketOdds]:
    if not candidate_ids:
        return {}
    rows = db.query(MarketOdds).filter(MarketOdds.candidate_id.in_(candidate_ids)).all()
    return {row.candidate_id: row for row in rows}


def update_market_odds(db: Session, candidate_id: int, scraped: ScrapedMarketOdds) -> MarketOdds:
    """Upserts the one current row for this candidate in place."""
    row = db.query(MarketOdds).filter(MarketOdds.candidate_id == candidate_id).first()
    if row is None:
        row = MarketOdds(candidate_id=candidate_id, ticker=scraped.ticker, yes_price_pct=0, as_of=scraped.as_of, source_url="")
        db.add(row)

    row.ticker = scraped.ticker
    row.yes_price_pct = scraped.yes_price_pct
    row.as_of = scraped.as_of
    row.source_url = scraped.source_url
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row
