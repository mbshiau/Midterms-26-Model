from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.models import Poll, PollResult, Race
from app.routers.deps import get_race_or_404
from app.schemas import PollOut
from app.services.pollster_ratings import get_pollster_ratings_by_name
from app.services.weighting import poll_weights

router = APIRouter(prefix="/races/{state_code}/polls", tags=["polls"])


@router.get("", response_model=list[PollOut])
def list_polls(race: Race = Depends(get_race_or_404), db: Session = Depends(get_db)):
    polls = (
        db.query(Poll)
        .filter(Poll.race_id == race.id)
        .options(selectinload(Poll.results).selectinload(PollResult.candidate))
        .order_by(desc(Poll.field_end_date))
        .all()
    )
    # Same pollster-quality-adjusted weighting the forecast itself uses (see
    # app.services.forecasting.generate_forecast), so this displayed weight
    # column always matches what actually fed the model.
    pollster_ratings = get_pollster_ratings_by_name(db)
    weights = poll_weights(polls, date.today(), settings.recency_half_life_days, pollster_ratings)
    return [
        PollOut.model_validate(poll).model_copy(update={"weight": weights[poll.id]})
        for poll in polls
    ]
