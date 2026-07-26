from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChamberControlHistoryPointOut, ChamberControlOut
from app.services.chamber_control import chamber_control_history, simulate_chamber_control

router = APIRouter(prefix="/chamber-control", tags=["chamber-control"])


@router.get("/senate", response_model=ChamberControlOut)
def get_senate_control(db: Session = Depends(get_db)):
    return simulate_chamber_control(db, office="Senate")


@router.get("/senate/history", response_model=list[ChamberControlHistoryPointOut])
def get_senate_control_history(db: Session = Depends(get_db)):
    return chamber_control_history(db, office="Senate")
