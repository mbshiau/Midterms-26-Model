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
from app.services.forecasting import race_movement_summaries
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


def _candidates_by_race(db: Session, races: list[Race]) -> dict[int, list[Candidate]]:
    race_ids = [race.id for race in races]
    if not race_ids:
        return {}
    by_race: dict[int, list[Candidate]] = {}
    for candidate in db.query(Candidate).filter(Candidate.race_id.in_(race_ids)).all():
        by_race.setdefault(candidate.race_id, []).append(candidate)
    return by_race


@router.get("", response_model=list[RaceOut])
def list_races(db: Session = Depends(get_db)):
    races = db.query(Race).order_by(Race.state_name).all()
    candidates_by_race = _candidates_by_race(db, races)
    return [_race_out(race, candidates_by_race.get(race.id, [])) for race in races]


@router.get("/summary", response_model=list[RaceSummaryOut])
def list_race_summaries(office: str | None = None, db: Session = Depends(get_db)):
    """Bulk row per race for the map page -- one request instead of the map
    page's previous N x (/forecast + /forecast/history) fan-out, which on a
    resource-limited host (e.g. Render's free tier) queued up badly once
    forecast history got deep. Candidates and forecast movement are each
    fetched in one bulk query for the whole office rather than per-race --
    with House now at 435 districts, per-race round trips were the dominant
    cost of loading this endpoint. See app.services.forecasting.
    race_movement_summaries for the movement-query plan."""
    query = db.query(Race)
    if office:
        query = query.filter(Race.office == office)
    races = query.order_by(Race.state_name).all()

    candidates_by_race = _candidates_by_race(db, races)
    movement_by_race = race_movement_summaries(db, races)

    out = []
    for race in races:
        candidates = candidates_by_race.get(race.id, [])
        latest_created_at, latest_rows, since_refresh, this_week = movement_by_race[race.id]

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
