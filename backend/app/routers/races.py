from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Race
from app.schemas import RaceOut

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=list[RaceOut])
def list_races(db: Session = Depends(get_db)):
    return db.query(Race).order_by(Race.state_name).all()
