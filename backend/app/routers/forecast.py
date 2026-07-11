from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.data.fundamentals_data import ELECTION_DATE
from app.database import get_db
from app.models import ActualResult
from app.schemas import ForecastHistoryOut, ForecastSnapshotOut
from app.services.forecasting import forecast_history, latest_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastSnapshotOut)
def get_latest_forecast(db: Session = Depends(get_db)):
    snapshot = latest_forecast(db)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No forecast yet. POST /simulate to generate one.",
        )
    return snapshot


@router.get("/history", response_model=ForecastHistoryOut)
def get_forecast_history(db: Session = Depends(get_db)):
    snapshots = forecast_history(db)
    actuals = db.query(ActualResult).all()
    return ForecastHistoryOut(
        snapshots=snapshots,
        actuals=actuals,
        election_date=ELECTION_DATE,
    )
