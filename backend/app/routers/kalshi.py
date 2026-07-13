from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Race
from app.routers.deps import get_race_or_404
from app.schemas import KalshiOddsOut
from app.services.market_odds import get_market_odds

router = APIRouter(prefix="/races/{state_code}/kalshi", tags=["kalshi"])


@router.get("", response_model=list[KalshiOddsOut])
def list_kalshi_odds(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    """Standalone Kalshi prediction-market odds for this race's candidates --
    not part of the forecasting model, just a separate reference display.
    Only candidates with a live market (kalshi_ticker set and at least one
    successful scrape) appear here; empty list if none do yet."""
    candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
    market_odds = get_market_odds(db, [c.id for c in candidates])
    by_id = {c.id: c for c in candidates}

    return [
        KalshiOddsOut(
            candidate=by_id[candidate_id],
            ticker=row.ticker,
            win_probability_pct=row.yes_price_pct,
            as_of=row.as_of,
            source_url=row.source_url,
        )
        for candidate_id, row in market_odds.items()
    ]
