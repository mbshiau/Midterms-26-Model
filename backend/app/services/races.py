"""Seeds/looks up Race rows from the static app.seed.seed_data.RACES registry
— the single place that defines which states have a model built."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Race
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
