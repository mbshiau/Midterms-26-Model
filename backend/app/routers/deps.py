from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Race
from app.services.races import get_race


def get_race_or_404(state_code: str, db: Session = Depends(get_db)) -> Race:
    race = get_race(db, state_code)
    if race is None:
        raise HTTPException(status_code=404, detail=f"no race found for state {state_code!r}")
    return race
