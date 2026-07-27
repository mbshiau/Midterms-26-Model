"""Seeds/looks up Race rows from the static seed registries (RACES for
Governor, SENATE_RACES for Senate, HOUSE_RACES for House -- see
app.seed.seed_data / app.seed.house_seed_data) -- the single place that
defines which state/office/district combos have a model built.

Every race is identified externally by `slug` (Race.slug, e.g. "pa-gov" /
"mi-sen" / "ca-house-12") rather than bare state_code, since a state can
have a Governor race, a Senate race, and many House races all at once.
`_parse_slug` is the inverse of Race.slug (app/models.py) -- state_code is
always exactly 2 chars, so splitting on "-" is unambiguous."""

from datetime import date

from sqlalchemy.orm import Session

from app.data.district_fundamentals_data import DISTRICT_FUNDAMENTALS
from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Candidate, Race
from app.seed.house_seed_data import HOUSE_RACES
from app.seed.seed_data import RACES as RACE_SEED_DATA
from app.seed.seed_data import SENATE_RACES as SENATE_SEED_DATA

_OFFICE_BY_SLUG_ABBREV = {"gov": "Governor", "sen": "Senate"}
_ELECTIONS_KEY_BY_OFFICE = {
    "Governor": "gubernatorial_elections",
    "Senate": "senate_elections",
    "House": "house_elections",
}
_SEED_REGISTRY_BY_OFFICE = {"Governor": RACE_SEED_DATA, "Senate": SENATE_SEED_DATA, "House": HOUSE_RACES}


def _district_key(state_code: str, district: int) -> str:
    """The 4-char key HOUSE_RACES/DISTRICT_FUNDAMENTALS use, e.g. "ca12"."""
    return f"{state_code}{district:02d}"


def _parse_slug(slug: str) -> tuple[str, str, int] | None:
    """Governor/Senate slugs are 2-part ("pa-gov"); House is 3-part
    ("ca-house-12") since a state can have many House races. Returns
    (state_code, office, district) -- district is 0 for Governor/Senate."""
    parts = slug.lower().split("-")
    if len(parts) < 2:
        return None
    state_code = parts[0]
    if len(parts) == 2:
        office = _OFFICE_BY_SLUG_ABBREV.get(parts[1])
        if office is None:
            return None
        return state_code, office, 0
    if len(parts) == 3 and parts[1] == "house":
        try:
            district = int(parts[2])
        except ValueError:
            return None
        return state_code, "House", district
    return None


def _seed_registry(office: str) -> dict:
    return _SEED_REGISTRY_BY_OFFICE[office]


def seed_all_races(db: Session) -> dict[str, Race]:
    """Ensures a Race row exists for every state/office/district combo in
    the seed registries. Returns {slug: Race}."""
    existing = {(r.state_code, r.office, r.district): r for r in db.query(Race).all()}
    for office, registry in (("Governor", RACE_SEED_DATA), ("Senate", SENATE_SEED_DATA), ("House", HOUSE_RACES)):
        for reg_key, seed in registry.items():
            district = seed.get("district", 0)
            state_code = reg_key[:2] if office == "House" else reg_key
            key = (state_code, office, district)
            if key in existing:
                continue
            race = Race(
                state_code=state_code,
                state_name=seed["state_name"],
                office=seed.get("office", office),
                district=district,
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
    state_code, office, district = parsed
    return (
        db.query(Race)
        .filter(Race.state_code == state_code, Race.office == office, Race.district == district)
        .first()
    )


def get_race_seed(slug: str) -> dict:
    state_code, office, district = _parse_slug(slug)
    registry = _seed_registry(office)
    reg_key = _district_key(state_code, district) if office == "House" else state_code
    return registry[reg_key]


def get_race_fundamentals(race: Race) -> dict:
    """The single place that resolves "which fundamentals blob does this
    race use" -- RACE_FUNDAMENTALS is keyed one-per-state (correct for
    Governor/Senate, at most one race per state); House needs one entry
    per *district* instead, so it reads DISTRICT_FUNDAMENTALS keyed by
    _district_key. See app.services.forecasting/chamber_control, which
    call this instead of indexing RACE_FUNDAMENTALS directly."""
    if race.office == "House":
        return DISTRICT_FUNDAMENTALS[_district_key(race.state_code, race.district)]
    return RACE_FUNDAMENTALS[race.state_code]


def current_holder_party(race: Race, candidates: list[Candidate]) -> str:
    """Which party currently holds this seat -- used to detect a projected
    flip. For a race with a candidate running for reelection, that's simply
    their party. For an open seat (no candidate is the incumbent), it's
    derived from the winning party of the most recent real election on file
    for this race's own office (governor, Senate, or this specific House
    district), since that officeholder's term runs through this year's
    election regardless of whether they're on the ballot again."""
    for candidate in candidates:
        if candidate.incumbent:
            return candidate.party

    elections_key = _ELECTIONS_KEY_BY_OFFICE.get(race.office, "gubernatorial_elections")
    elections = get_race_fundamentals(race)[elections_key]
    if not elections:
        # No historical election on file (e.g. a House district scaffolded
        # with empty house_elections and no incumbent seeded yet) -- no
        # real basis to call a holder party one way or the other.
        return "Independent"
    last_election = elections[-1]
    return "Democratic" if last_election["dem_share"] > 50 else "Republican"
