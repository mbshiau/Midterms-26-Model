from datetime import date

import pytest

from app.config import settings
from app.data.fundamentals_data import RACE_FUNDAMENTALS
from app.database import Base
from app.models import Candidate, Race
from app.services.forecasting import blend_with_fundamentals, generate_forecast
from app.services.weighting import CandidateAverage

PA = RACE_FUNDAMENTALS["pa"]


def test_blend_is_a_linear_interpolation_between_polling_and_fundamentals():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=True)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=70.0, weighted_std=2.0, n_polls=5),
        2: CandidateAverage(candidate_id=2, weighted_mean=30.0, weighted_std=2.0, n_polls=5),
    }

    alpha = 0.8
    blended, fundamentals_shares = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], alpha, date(2026, 7, 10), 37.0, "Republican"
    )

    expected_dem_mean = alpha * 70.0 + (1 - alpha) * fundamentals_shares[1]
    assert abs(blended[1].weighted_mean - expected_dem_mean) < 1e-9

    # blended mean must sit strictly between the two pre-blend inputs
    # (this is a pure linear interpolation, unlike the post-simulation mean)
    lo, hi = sorted([70.0, fundamentals_shares[1]])
    assert lo <= blended[1].weighted_mean <= hi


def test_blend_widens_uncertainty_relative_to_polling_alone():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=True)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=55.0, weighted_std=1.0, n_polls=5),
        2: CandidateAverage(candidate_id=2, weighted_mean=45.0, weighted_std=1.0, n_polls=5),
    }

    blended, _ = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], 0.5, date(2026, 7, 10), 37.0, "Republican"
    )

    assert blended[1].weighted_std > polling_averages[1].weighted_std


def test_alpha_one_ignores_fundamentals_entirely():
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=False)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    polling_averages = {
        1: CandidateAverage(candidate_id=1, weighted_mean=48.0, weighted_std=3.0, n_polls=2),
        2: CandidateAverage(candidate_id=2, weighted_mean=52.0, weighted_std=3.0, n_polls=2),
    }

    blended, _ = blend_with_fundamentals(
        PA, polling_averages, [dem, rep], 1.0, date(2026, 7, 10), 37.0, "Republican"
    )

    assert blended[1].weighted_mean == polling_averages[1].weighted_mean
    assert blended[1].weighted_std == polling_averages[1].weighted_std


def test_blend_falls_back_to_fundamentals_only_when_no_polling_exists():
    # A race with zero real polls yet (e.g. a just-settled matchup with no
    # published polling) must still produce a full forecast for every
    # candidate, using the fundamentals estimate directly rather than
    # fabricating a polling number or omitting the candidate.
    dem = Candidate(id=1, name="Dem Candidate", party="Democratic", incumbent=False)
    rep = Candidate(id=2, name="Rep Candidate", party="Republican", incumbent=False)

    blended, fundamentals_shares = blend_with_fundamentals(
        PA, {}, [dem, rep], 0.0, date(2026, 7, 10), 37.0, "Republican"
    )

    assert set(blended.keys()) == {1, 2}
    assert blended[1].weighted_mean == fundamentals_shares[1]
    assert blended[2].weighted_mean == fundamentals_shares[2]
    assert blended[1].weighted_std == settings.fundamentals_uncertainty_stdev
    assert blended[1].n_polls == 0


@pytest.fixture()
def tables(test_engine):
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture()
def pa_race(db_session, tables):
    race = Race(
        state_code="pa",
        state_name="Pennsylvania",
        election_date=date(2026, 11, 3),
        wikipedia_page_title="2026_Pennsylvania_gubernatorial_election",
    )
    db_session.add(race)
    db_session.flush()
    db_session.add(Candidate(race_id=race.id, name="Dem Candidate", party="Democratic", incumbent=True))
    db_session.add(Candidate(race_id=race.id, name="Rep Candidate", party="Republican", incumbent=False))
    db_session.commit()
    return race


def test_generate_forecast_wires_in_the_national_shock(db_session, pa_race):
    # With a fixed seed (isolating idiosyncratic noise), the only thing that
    # can differ between two otherwise-identical calls is the date-derived
    # national shock -- so a real difference in mean_vote_share proves
    # generate_forecast is actually threading it through end to end, not
    # just that the underlying simulation primitives support it in isolation.
    snapshot_day1 = generate_forecast(db_session, pa_race, seed=42, as_of=date(2026, 7, 15))
    snapshot_day2 = generate_forecast(db_session, pa_race, seed=42, as_of=date(2026, 7, 16))

    dem_day1 = next(r for r in snapshot_day1.results if r.candidate.party == "Democratic")
    dem_day2 = next(r for r in snapshot_day2.results if r.candidate.party == "Democratic")

    assert dem_day1.mean_vote_share != dem_day2.mean_vote_share


def test_generate_forecast_is_reproducible_for_the_same_seed_and_date(db_session, pa_race):
    snapshot_a = generate_forecast(db_session, pa_race, seed=42, as_of=date(2026, 7, 15))
    snapshot_b = generate_forecast(db_session, pa_race, seed=42, as_of=date(2026, 7, 15))

    dem_a = next(r for r in snapshot_a.results if r.candidate.party == "Democratic")
    dem_b = next(r for r in snapshot_b.results if r.candidate.party == "Democratic")

    assert dem_a.mean_vote_share == dem_b.mean_vote_share
