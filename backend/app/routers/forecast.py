from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActualResult, Candidate, Race
from app.routers.deps import get_race_or_404
from app.schemas import ForecastHistoryOut, ForecastSnapshotOut
from app.services.forecasting import forecast_history, latest_forecast

router = APIRouter(prefix="/races/{slug}/forecast", tags=["forecast"])


@router.get("", response_model=ForecastSnapshotOut)
def get_latest_forecast(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    snapshot = latest_forecast(db, race)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No forecast yet. POST /simulate to generate one.",
        )
    return snapshot


@router.get("/history", response_model=ForecastHistoryOut)
def get_forecast_history(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    snapshots = forecast_history(db, race)
    actuals = (
        db.query(ActualResult)
        .join(Candidate, ActualResult.candidate_id == Candidate.id)
        .filter(Candidate.race_id == race.id)
        .all()
    )
    return ForecastHistoryOut(
        snapshots=snapshots,
        actuals=actuals,
        election_date=race.election_date,
    )
