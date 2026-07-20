from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Race
from app.routers.deps import get_race_or_404
from app.schemas import RaceIntelligenceOut
from app.services.race_intelligence import get_race_intelligence_view

router = APIRouter(prefix="/races/{slug}/intelligence", tags=["intelligence"])


@router.get("", response_model=RaceIntelligenceOut)
def get_race_intelligence(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    """Recent headlines, cached AI news/market-comparison text, and a
    "what changed since the last refresh" summary -- display-only context
    alongside the forecast, never part of the model itself (see
    app.services.race_intelligence)."""
    return get_race_intelligence_view(db, race)
