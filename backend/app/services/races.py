"""Seeds/looks up Race rows from the static app.seed.seed_data registries
(RACES for Governor, SENATE_RACES for Senate) -- the single place that
defines which state/office pairs have a model built.

Every race is identified externally by `slug` (Race.slug, e.g. "pa-gov" /
"mi-sen") rather than bare state_code, since a state can have both a
Governor and a Senate race at once. `_parse_slug` is the inverse of
Race.slug (app/models.py) -- state_code is always exactly 2 chars, so
splitting on the first "-" is unambiguous."""

from datetime import date

from sqlalchemy.orm import Session

from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Candidate, Race
from app.seed.seed_data import RACES as RACE_SEED_DATA
from app.seed.seed_data import SENATE_RACES as SENATE_SEED_DATA

_OFFICE_BY_SLUG_ABBREV = {"gov": "Governor", "sen": "Senate"}
_ELECTIONS_KEY_BY_OFFICE = {"Governor": "gubernatorial_elections", "Senate": "senate_elections"}


def _parse_slug(slug: str) -> tuple[str, str] | None:
    state_code, _, abbrev = slug.lower().partition("-")
    office = _OFFICE_BY_SLUG_ABBREV.get(abbrev)
    if office is None:
        return None
    return state_code, office


def _seed_registry(office: str) -> dict:
    return RACE_SEED_DATA if office == "Governor" else SENATE_SEED_DATA


def seed_all_races(db: Session) -> dict[str, Race]:
    """Ensures a Race row exists for every state/office pair in the seed
    registries. Returns {slug: Race}."""
    existing = {(r.state_code, r.office): r for r in db.query(Race).all()}
    for office, registry in (("Governor", RACE_SEED_DATA), ("Senate", SENATE_SEED_DATA)):
        for state_code, seed in registry.items():
            key = (state_code, office)
            if key in existing:
                continue
            race = Race(
                state_code=state_code,
                state_name=seed["state_name"],
                office=seed.get("office", office),
                election_date=date.fromisoformat(seed["election_date"]),
                wikipedia_page_title=seed["wikipedia_page_title"],
            )
            db.add(race)
            db.flush()
            existing[key] = race
    db.commit()
    return {race.slug: race for race in existing.values()}


def get_race(db: Session, slug: str) -> Race | None:
    parsed = _parse_slug(slug)
    if parsed is None:
        return None
    state_code, office = parsed
    return db.query(Race).filter(Race.state_code == state_code, Race.office == office).first()


def get_race_seed(slug: str) -> dict:
    state_code, office = _parse_slug(slug)
    return _seed_registry(office)[state_code]


def current_holder_party(race: Race, candidates: list[Candidate]) -> str:
    """Which party currently holds this seat -- used to detect a projected
    flip. For a race with a candidate running for reelection, that's simply
    their party. For an open seat (no candidate is the incumbent), it's
    derived from the winning party of the most recent real election on file
    for this race's own office (governor or Senate), since that
    officeholder's term runs through this year's election regardless of
    whether they're on the ballot again."""
    for candidate in candidates:
        if candidate.incumbent:
            return candidate.party

    elections_key = _ELECTIONS_KEY_BY_OFFICE.get(race.office, "gubernatorial_elections")
    last_election = RACE_FUNDAMENTALS[race.state_code.lower()][elections_key][-1]
    return "Democratic" if last_election["dem_share"] > 50 else "Republican"
