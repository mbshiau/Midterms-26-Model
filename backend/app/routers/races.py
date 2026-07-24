from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Race
from app.schemas import (
    RaceOut,
    RaceSummaryCandidateOut,
    RaceSummaryDeltaOut,
    RaceSummaryOut,
    _as_utc_isoformat,
)
from app.services.forecasting import race_movement_summary
from app.services.races import current_holder_party

router = APIRouter(prefix="/races", tags=["races"])


def _race_out(race: Race, candidates: list[Candidate]) -> RaceOut:
    return RaceOut(
        slug=race.slug,
        state_code=race.state_code,
        state_name=race.state_name,
        office=race.office,
        election_date=race.election_date,
        current_holder_party=current_holder_party(race, candidates),
    )


@router.get("", response_model=list[RaceOut])
def list_races(db: Session = Depends(get_db)):
    races = db.query(Race).order_by(Race.state_name).all()
    out = []
    for race in races:
        candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
        out.append(_race_out(race, candidates))
    return out


@router.get("/summary", response_model=list[RaceSummaryOut])
def list_race_summaries(office: str | None = None, db: Session = Depends(get_db)):
    """Bulk row per race for the map page -- one request instead of the map
    page's previous N x (/forecast + /forecast/history) fan-out, which on a
    resource-limited host (e.g. Render's free tier) queued up badly once
    forecast history got deep. See app.services.forecasting.
    race_movement_summary for what's actually queried per race."""
    query = db.query(Race)
    if office:
        query = query.filter(Race.office == office)
    races = query.order_by(Race.state_name).all()

    out = []
    for race in races:
        candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
        latest_created_at, latest_rows, since_refresh, this_week = race_movement_summary(db, race)

        out.append(
            RaceSummaryOut(
                race=_race_out(race, candidates),
                latest_forecast_created_at=(
                    _as_utc_isoformat(latest_created_at) if latest_created_at else None
                ),
                candidates=[RaceSummaryCandidateOut(**r) for r in latest_rows],
                since_refresh=[RaceSummaryDeltaOut(**d) for d in since_refresh] if since_refresh else None,
                this_week=[RaceSummaryDeltaOut(**d) for d in this_week] if this_week else None,
            )
        )
    return out
