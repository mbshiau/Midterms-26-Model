"""Seeds/looks up Race rows from the static app.seed.seed_data.RACES registry
— the single place that defines which states have a model built."""

from datetime import date

from sqlalchemy.orm import Session

from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Candidate, Race
from app.seed.seed_data import RACES as RACE_SEED_DATA


def seed_all_races(db: Session) -> dict[str, Race]:
    """Ensures a Race row exists for every state in the seed registry.
    Returns {state_code: Race}."""
    existing = {r.state_code: r for r in db.query(Race).all()}
    for state_code, seed in RACE_SEED_DATA.items():
        if state_code in existing:
            continue
        race = Race(
            state_code=state_code,
            state_name=seed["state_name"],
            office=seed.get("office", "Governor"),
            election_date=date.fromisoformat(seed["election_date"]),
            wikipedia_page_title=seed["wikipedia_page_title"],
        )
        db.add(race)
        db.flush()
        existing[state_code] = race
    db.commit()
    return existing


def get_race(db: Session, state_code: str) -> Race | None:
    return db.query(Race).filter(Race.state_code == state_code.lower()).first()


def get_race_seed(state_code: str) -> dict:
    return RACE_SEED_DATA[state_code.lower()]


def current_holder_party(state_code: str, candidates: list[Candidate]) -> str:
    """Which party currently holds this seat -- used to detect a projected
    flip. For a race with a candidate running for reelection, that's simply
    their party. For an open seat (no candidate is the incumbent), it's
    derived from the winning party of the most recent real gubernatorial
    election on file, since that officeholder's term runs through this
    year's election regardless of whether they're on the ballot again."""
    for candidate in candidates:
        if candidate.incumbent:
            return candidate.party

    last_election = RACE_FUNDAMENTALS[state_code.lower()]["gubernatorial_elections"][-1]
    return "Democratic" if last_election["dem_share"] > 50 else "Republican"
