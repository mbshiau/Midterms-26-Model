from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Race
from app.schemas import RaceOut
from app.services.races import current_holder_party

router = APIRouter(prefix="/races", tags=["races"])


@router.get("", response_model=list[RaceOut])
def list_races(db: Session = Depends(get_db)):
    races = db.query(Race).order_by(Race.state_name).all()
    out = []
    for race in races:
        candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
        out.append(
            RaceOut(
                slug=race.slug,
                state_code=race.state_code,
                state_name=race.state_name,
                office=race.office,
                election_date=race.election_date,
                current_holder_party=current_holder_party(race, candidates),
            )
        )
    return out
