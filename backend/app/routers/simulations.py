import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Race
from app.routers.deps import get_race_or_404
from app.schemas import (
    ForecastSnapshotOut,
    SimulateRequest,
    SimulationHistogramOut,
    SimulationsOut,
)
from app.services.forecasting import generate_forecast, latest_forecast
from app.services.simulation import histogram

router = APIRouter(prefix="/races/{state_code}", tags=["simulations"])


@router.post("/simulate", response_model=ForecastSnapshotOut)
def simulate(
    req: SimulateRequest, race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)
):
    try:
        snapshot = generate_forecast(
            db,
            race,
            n_simulations=req.n_simulations,
            recency_half_life_days=req.recency_half_life_days,
            historical_error_stdev=req.historical_error_stdev,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return snapshot


@router.get("/simulations", response_model=SimulationsOut)
def get_simulations(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    snapshot = latest_forecast(db, race)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No forecast yet. POST /simulate to generate one.",
        )

    histograms = []
    for result in snapshot.results:
        draws = np.array(result.draws_sample)
        bin_edges, counts = histogram(draws)
        histograms.append(
            SimulationHistogramOut(
                candidate=result.candidate,
                bin_edges=bin_edges,
                counts=counts,
                draws_sample=result.draws_sample,
            )
        )

    return SimulationsOut(
        snapshot_id=snapshot.id,
        created_at=snapshot.created_at,
        n_simulations=snapshot.n_simulations,
        histograms=histograms,
    )
