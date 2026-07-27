from datetime import date

from app.data.district_fundamentals_data import DISTRICT_FUNDAMENTALS
from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.models import Race
from app.services.races import _district_key, _parse_slug, get_race_fundamentals


def test_governor_slug_round_trips():
    race = Race(state_code="pa", state_name="Pennsylvania", office="Governor", district=0,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert race.slug == "pa-gov"
    assert _parse_slug(race.slug) == ("pa", "Governor", 0)


def test_senate_slug_round_trips():
    race = Race(state_code="oh", state_name="Ohio", office="Senate", district=0,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert race.slug == "oh-sen"
    assert _parse_slug(race.slug) == ("oh", "Senate", 0)


def test_house_slug_round_trips_with_zero_padded_district():
    race = Race(state_code="ca", state_name="California", office="House", district=12,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert race.slug == "ca-house-12"
    assert _parse_slug(race.slug) == ("ca", "House", 12)


def test_house_slug_round_trips_for_at_large_district():
    race = Race(state_code="ak", state_name="Alaska", office="House", district=1,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert race.slug == "ak-house-01"
    assert _parse_slug(race.slug) == ("ak", "House", 1)


def test_parse_slug_rejects_garbage():
    assert _parse_slug("not-a-real-slug") is None
    assert _parse_slug("xx-house-notanumber") is None
    assert _parse_slug("solo") is None


def test_district_key_formats_state_and_district():
    assert _district_key("ca", 1) == "ca01"
    assert _district_key("ca", 12) == "ca12"


def test_get_race_fundamentals_dispatches_to_race_fundamentals_for_governor():
    race = Race(state_code="pa", state_name="Pennsylvania", office="Governor", district=0,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert get_race_fundamentals(race) is RACE_FUNDAMENTALS["pa"]


def test_get_race_fundamentals_dispatches_to_district_fundamentals_for_house():
    key = next(iter(DISTRICT_FUNDAMENTALS))
    state_code, district = key[:2], int(key[2:])
    race = Race(state_code=state_code, state_name="x", office="House", district=district,
                election_date=date(2026, 11, 3), wikipedia_page_title="x")
    assert get_race_fundamentals(race) is DISTRICT_FUNDAMENTALS[key]
