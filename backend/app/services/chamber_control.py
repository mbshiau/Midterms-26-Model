"""Aggregates every race in a chamber (currently just Senate) into a joint
seat-count distribution, respecting the same correlated national-error
structure each individual race's forecast already uses (see
app.services.simulation.generate_national_shock) -- a shared national
polling miss should move every state's simulated outcome together, so the
33 Class-2 races can't just be combined draw-by-draw unless they were all
generated against the *same* national_shock array.

Deliberately does NOT reuse each race's separately-stored "latest"
ForecastSnapshot for this, since those are refreshed independently (a manual
/simulate call, or the scheduled job catching up after a missed run) and can
drift to different `as_of` dates -- which would silently decorrelate them
(see generate_national_shock's date-seeded determinism) and understate the
real joint uncertainty. Instead this recomputes a fresh, mutually consistent
batch of per-race simulations sharing one national_shock array and
n_simulations count -- the numpy simulation itself is on the order of
milliseconds, but the per-race DB fetches (33 races' worth of Poll +
fundamentals lookups) add up to roughly a second in practice, so
simulate_chamber_control caches its result for a couple minutes rather than
persisting a dedicated snapshot table (see _CACHE_TTL_SECONDS below) -- not
full-day storage, just enough to collapse several page loads seconds apart
into one real computation.

Independent candidates who have publicly declined to commit to caucusing
with either party (Bodnar/mt-sen, Bengs/sd-sen, Osborn/ne-sen -- unlike
sitting independents Sanders/King, who reliably caucus Democratic and are
folded into the real current-composition baseline below) don't count toward
either party's seat total and don't caucus as a bloc with anyone, so an
organizing vote comes down to a straight comparison of the Democratic bloc
against the Republican bloc -- see the dem_control/rep_control comparison
below for why that means a plain "more seats wins, ties go to the VP's
party" rule rather than a separate "independents hold the balance" outcome.
"""

import bisect
import hashlib
import time
from dataclasses import dataclass
from datetime import date

import numpy as np
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Candidate, ForecastResult, ForecastSnapshot, Poll, Race
from app.services.approval import get_current_approval
from app.services.forecasting import blend_with_fundamentals
from app.services.fundamentals import poll_weight_for_election
from app.services.generic_ballot import get_current_generic_ballot
from app.services.pollster_ratings import get_pollster_ratings_by_name
from app.services.races import current_holder_party, get_race_fundamentals
from app.services.simulation import generate_national_shock, run_monte_carlo
from app.services.weighting import two_party_normalize, weighted_polling_averages

# Current real-world Senate composition (119th Congress), verified via
# Wikipedia as of 2026-07-26 (post Lindsey Graham's July 2026 death +
# successor appointment): 53 R / 47 D, where the 47 already folds in the two
# sitting independents (Sanders, King) who reliably caucus Democratic. This
# is the full 100-seat chamber; subtracting the 33 modeled Class-2 seats'
# *current* holders (below) leaves the fixed Class-1/3 baseline that isn't
# up for election this cycle at all.
CURRENT_SENATE_TOTAL_DEM = 47
CURRENT_SENATE_TOTAL_REP = 53

# See module docstring -- these three have each explicitly declined to say
# they'd caucus with either party if elected.
UNCOMMITTED_INDEPENDENT_PARTY = "Independent"

# Matches the frontend's SIMULATIONS_PER_DOT (SenateControlChart.tsx) -- each
# rendered dot gets its own representative draw from roughly this many
# simulations, rather than the whole column sharing one example.
SIMULATIONS_PER_DOT = 100


def _race_simulation_seed(as_of: date, race_id: int) -> int:
    """Stable across process restarts and identical for every request on the
    same calendar day, so repeated hits to /chamber-control/senate (e.g. the
    home page orb and the Senate page's own control chart, loaded seconds
    apart) return the same dem_win_probability/rep_win_probability instead
    of drifting with fresh Monte Carlo noise each time."""
    digest = hashlib.sha256(f"{as_of.isoformat()}:{race_id}".encode()).hexdigest()
    return int(digest, 16) % (2**32)


@dataclass
class SeatDot:
    rep_seats: int
    independent_seats: int
    count: int
    probability: float
    example_race_winners: list[dict]


@dataclass
class SeatScenario:
    dem_seats: int
    count: int
    probability: float
    dominant_outcome: str
    dots: list[SeatDot]


@dataclass
class ChamberControlResult:
    as_of: date
    n_simulations: int
    safe_dem_seats: int
    safe_rep_seats: int
    dem_win_probability: float
    rep_win_probability: float
    seat_distribution: list[SeatScenario]


# Both call sites (the /chamber-control/senate route, and
# chamber_control_history's "pin today's point to the live number" below)
# hit this with default n_simulations/error_stdev/half_life -- every real
# request for a given (office, as_of) is computing the exact same numbers as
# _race_simulation_seed already guarantees (deterministic per calendar day),
# so redoing the full per-race DB fetch + 10k-draw Monte Carlo on every
# single page load is pure waste, not fresher data. Measured at ~1s per call
# in practice (33 Senate races' worth of poll queries + fundamentals lookups
# dominates, not the numpy simulation itself the module docstring assumed
# was "cheap enough") -- and it was one of only three things gating the home
# page's initial render. A short TTL (not the full day, unlike the
# same-day-deterministic seed) keeps a manual mid-day refresh's new polls
# showing up within a couple minutes rather than only at the next calendar
# day, while collapsing the common case -- several page loads seconds apart
# -- to one real computation. Bypassed entirely when a caller passes
# explicit simulation parameters (only tests would ever do this), so it
# can't mask a deliberately-different scenario.
_CACHE_TTL_SECONDS = 120
_result_cache: dict[str, tuple[float, "ChamberControlResult"]] = {}


def simulate_chamber_control(
    db: Session,
    office: str = "Senate",
    as_of: date | None = None,
    n_simulations: int | None = None,
    historical_error_stdev: float | None = None,
    recency_half_life_days: float | None = None,
) -> ChamberControlResult:
    as_of = as_of or date.today()
    uses_default_params = (
        n_simulations is None and historical_error_stdev is None and recency_half_life_days is None
    )
    cache_key = f"{office}:{as_of.isoformat()}"
    if uses_default_params:
        cached = _result_cache.get(cache_key)
        if cached is not None and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

    result = _compute_chamber_control(
        db, office, as_of, n_simulations, historical_error_stdev, recency_half_life_days
    )

    if uses_default_params:
        _result_cache[cache_key] = (time.monotonic(), result)
    return result


def _compute_chamber_control(
    db: Session,
    office: str,
    as_of: date,
    n_simulations: int | None,
    historical_error_stdev: float | None,
    recency_half_life_days: float | None,
) -> ChamberControlResult:
    n_simulations = n_simulations or settings.default_n_simulations
    half_life_days = recency_half_life_days or settings.recency_half_life_days
    error_stdev = historical_error_stdev or settings.historical_error_stdev

    races = db.query(Race).filter(Race.office == office).order_by(Race.state_name).all()

    pollster_ratings = get_pollster_ratings_by_name(db)
    approval = get_current_approval(db)
    generic_ballot = get_current_generic_ballot(db)
    generic_ballot_margin = generic_ballot.dem_pct - generic_ballot.rep_pct

    # One shock array shared by every race below -- the entire point is a
    # mutually consistent correlated national scenario at each draw index.
    national_shock = generate_national_shock(n_simulations, settings.national_error_stdev, as_of)

    modeled_dem_current = 0
    modeled_rep_current = 0
    race_meta: list[dict] = []
    winner_party_by_race: list[np.ndarray] = []

    for race in races:
        candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
        holder = current_holder_party(race, candidates)
        if holder == "Democratic":
            modeled_dem_current += 1
        elif holder == "Republican":
            modeled_rep_current += 1

        polls = (
            db.query(Poll)
            .filter(Poll.race_id == race.id)
            .options(selectinload(Poll.results))
            .all()
        )
        fundamentals_data = get_race_fundamentals(race)
        polling_averages = two_party_normalize(
            weighted_polling_averages(polls, as_of, half_life_days, pollster_ratings)
        )
        model_overrides = fundamentals_data.get("model_overrides", {})
        alpha = (
            poll_weight_for_election(
                race.election_date, as_of,
                floor=model_overrides.get("poll_weight_floor"),
                ceiling=model_overrides.get("poll_weight_ceiling"),
            )
            if polls else 0.0
        )
        blended_averages, _ = blend_with_fundamentals(
            fundamentals_data, polling_averages, candidates, alpha, as_of,
            approval.approval_pct, approval.party, generic_ballot_margin, race.office,
        )
        candidate_parties = {c.id: c.party for c in candidates}
        sim_results = run_monte_carlo(
            blended_averages, error_stdev, n_simulations,
            seed=_race_simulation_seed(as_of, race.id),
            candidate_parties=candidate_parties, national_shock=national_shock,
        )

        cids = list(sim_results.keys())
        draws_matrix = np.vstack([sim_results[cid].draws for cid in cids])
        winner_pos = np.argmax(draws_matrix, axis=0)
        candidates_by_id = {c.id: c for c in candidates}
        winner_parties = np.array([candidate_parties[cids[i]] for i in winner_pos])
        winner_names = np.array([candidates_by_id[cids[i]].name for i in winner_pos])
        # Winning margin per draw (winner's share minus the runner-up's) --
        # lets the scenario map shade each state by how close that
        # particular example was, not just a flat "someone won" fill.
        sorted_shares = np.sort(draws_matrix, axis=0)
        margin_by_draw = sorted_shares[-1] - sorted_shares[-2]

        winner_party_by_race.append(winner_parties)
        race_meta.append({
            "slug": race.slug,
            "state_code": race.state_code,
            "state_name": race.state_name,
            "names_by_draw": winner_names,
            "margin_by_draw": margin_by_draw,
        })

    safe_dem_seats = CURRENT_SENATE_TOTAL_DEM - modeled_dem_current
    safe_rep_seats = CURRENT_SENATE_TOTAL_REP - modeled_rep_current

    dem_seats = np.full(n_simulations, safe_dem_seats, dtype=int)
    rep_seats = np.full(n_simulations, safe_rep_seats, dtype=int)
    ind_seats = np.zeros(n_simulations, dtype=int)
    for winner_parties in winner_party_by_race:
        dem_seats += (winner_parties == "Democratic").astype(int)
        rep_seats += (winner_parties == "Republican").astype(int)
        ind_seats += (winner_parties == UNCOMMITTED_INDEPENDENT_PARTY).astype(int)

    # An uncommitted independent doesn't caucus with (or vote as a bloc
    # with) either side, so a Senate organizing vote comes down to a
    # straight comparison of the Democratic bloc against the Republican
    # bloc: whichever is larger already has a majority of votes actually
    # cast, independents or not. A tie between the two blocs goes to
    # Republicans, since they hold the vice presidency (JD Vance) and the
    # VP breaks a tie in whatever vote is actually equally divided -- not
    # only a literal 50-50 split of the full 100-seat chamber. So control is
    # fully decided by comparing dem_seats to rep_seats alone; there's no
    # separate "independents hold the balance" case once you assume
    # uncommitted independents don't swing the D-vs-R comparison itself.
    dem_control = dem_seats > rep_seats
    rep_control = ~dem_control

    dem_win_probability = float(np.mean(dem_control))
    rep_win_probability = float(np.mean(rep_control))

    # Bucketed by Dem-seat count for the dot plot's x-axis. A single
    # dem_seats total can still map to different rep/independent splits
    # (e.g. 50 Dem seats is a Democratic-control draw whenever at least one
    # independent also won, but a Republican-control draw -- tie broken by
    # the VP -- when zero did), so the column's fill color is whichever
    # outcome is the majority among the draws that landed on this total, not
    # a property of the total alone.
    buckets: dict[int, list[int]] = {}
    for i, total in enumerate(dem_seats.tolist()):
        buckets.setdefault(total, []).append(i)

    seat_distribution = []
    for total, indices in sorted(buckets.items()):
        dominant_outcome = (
            "Democratic" if bool(np.mean(dem_control[indices]) > 0.5) else "Republican"
        )

        # One dot per ~SIMULATIONS_PER_DOT draws in this bucket, each with
        # its own representative draw -- np.array_split spreads any
        # remainder across the chunks instead of leaving a short last dot.
        n_dots = max(1, round(len(indices) / SIMULATIONS_PER_DOT))
        dots = []
        for chunk in np.array_split(np.array(indices), n_dots):
            if chunk.size == 0:
                continue
            example_idx = int(chunk[0])
            example_winners = [
                {
                    "slug": meta["slug"],
                    "state_code": meta["state_code"],
                    "state_name": meta["state_name"],
                    "name": str(meta["names_by_draw"][example_idx]),
                    "party": str(winner_party_by_race[j][example_idx]),
                    "margin": float(meta["margin_by_draw"][example_idx]),
                }
                for j, meta in enumerate(race_meta)
            ]
            dots.append(
                SeatDot(
                    rep_seats=int(rep_seats[example_idx]),
                    independent_seats=int(ind_seats[example_idx]),
                    count=int(chunk.size),
                    probability=float(chunk.size) / n_simulations,
                    example_race_winners=example_winners,
                )
            )

        seat_distribution.append(
            SeatScenario(
                dem_seats=total,
                count=len(indices),
                probability=len(indices) / n_simulations,
                dominant_outcome=dominant_outcome,
                dots=dots,
            )
        )

    return ChamberControlResult(
        as_of=as_of,
        n_simulations=n_simulations,
        safe_dem_seats=safe_dem_seats,
        safe_rep_seats=safe_rep_seats,
        dem_win_probability=dem_win_probability,
        rep_win_probability=rep_win_probability,
        seat_distribution=seat_distribution,
    )


@dataclass
class ChamberControlHistoryPoint:
    as_of: date
    expected_dem_seats: float
    expected_rep_seats: float
    expected_independent_seats: float
    dem_win_probability: float
    rep_win_probability: float


def _independence_control_probabilities(
    per_race_probs: list[tuple[float, float, float]], safe_dem_seats: int, safe_rep_seats: int
) -> tuple[float, float]:
    """Poisson-binomial-style convolution: dist[d][r] is the probability of
    exactly d Dem seats and r Republican seats among the races folded in so
    far, treating every race as independent of every other. This is the
    documented simplification for the *historical* line only -- the live
    /chamber-control/senate endpoint uses a real correlated joint Monte
    Carlo (see simulate_chamber_control) since that data exists for today;
    there's no stored historical equivalent of the shared national_shock to
    reconstruct a true historical joint distribution, and treating each
    race as independent is the standard fallback -- it understates real
    tail uncertainty (a national polling miss tends to move every state the
    same way) but gives a genuine trend line rather than none at all."""
    size = 101
    dist = np.zeros((size, size))
    dist[safe_dem_seats, safe_rep_seats] = 1.0
    for p_dem, p_rep, p_ind in per_race_probs:
        shifted_dem = np.zeros((size, size))
        shifted_dem[1:, :] = dist[:-1, :]
        shifted_rep = np.zeros((size, size))
        shifted_rep[:, 1:] = dist[:, :-1]
        dist = shifted_dem * p_dem + shifted_rep * p_rep + dist * p_ind

    d_idx, r_idx = np.indices((size, size))
    dem_win = float(dist[d_idx > r_idx].sum())
    rep_win = float(dist[r_idx >= d_idx].sum())
    return dem_win, rep_win


def chamber_control_history(db: Session, office: str = "Senate") -> list[ChamberControlHistoryPoint]:
    """Expected-seats + independence-approximated control-probability, one
    point per calendar day any modeled race got a new forecast snapshot.
    Expected seats is exact regardless of correlation (expectation is
    linear: safe seats + sum of each race's own win probability, from that
    race's own stored history -- no joint simulation needed). Win
    probability is the independence approximation described on
    _independence_control_probabilities.

    Only dates on/after every race's *own* first snapshot are included --
    an earlier date would silently omit whichever races hadn't been seeded
    yet, understating both sides rather than reflecting a real day-over-day
    change."""
    races = db.query(Race).filter(Race.office == office).order_by(Race.state_name).all()

    modeled_dem_current = 0
    modeled_rep_current = 0
    per_race_snapshots: list[list[tuple[date, dict[str, float]]]] = []

    for race in races:
        candidates = db.query(Candidate).filter(Candidate.race_id == race.id).all()
        holder = current_holder_party(race, candidates)
        if holder == "Democratic":
            modeled_dem_current += 1
        elif holder == "Republican":
            modeled_rep_current += 1

        rows = (
            db.query(ForecastSnapshot.created_at, Candidate.party, ForecastResult.win_probability)
            .join(ForecastResult, ForecastResult.snapshot_id == ForecastSnapshot.id)
            .join(Candidate, ForecastResult.candidate_id == Candidate.id)
            .filter(ForecastSnapshot.race_id == race.id)
            .order_by(ForecastSnapshot.created_at.asc())
            .all()
        )
        by_day: dict[date, dict[str, float]] = {}
        for created_at, party, win_probability in rows:
            # Rows are ascending by created_at, so a later same-day snapshot
            # simply overwrites an earlier one for that day's entry.
            by_day.setdefault(created_at.date(), {})[party] = win_probability
        per_race_snapshots.append(sorted(by_day.items()))

    if not per_race_snapshots or any(len(s) == 0 for s in per_race_snapshots):
        return []

    safe_dem_seats = CURRENT_SENATE_TOTAL_DEM - modeled_dem_current
    safe_rep_seats = CURRENT_SENATE_TOTAL_REP - modeled_rep_current

    earliest_common_date = max(snapshots[0][0] for snapshots in per_race_snapshots)
    all_dates = sorted(
        {d for snapshots in per_race_snapshots for d, _ in snapshots if d >= earliest_common_date}
    )

    points = []
    for target_date in all_dates:
        expected_dem = float(safe_dem_seats)
        expected_rep = float(safe_rep_seats)
        expected_ind = 0.0
        per_race_probs: list[tuple[float, float, float]] = []

        for snapshots in per_race_snapshots:
            dates_only = [d for d, _ in snapshots]
            idx = bisect.bisect_right(dates_only, target_date) - 1
            probs = snapshots[idx][1]
            p_dem = probs.get("Democratic", 0.0)
            p_rep = probs.get("Republican", 0.0)
            p_ind = probs.get(UNCOMMITTED_INDEPENDENT_PARTY, 0.0)
            expected_dem += p_dem
            expected_rep += p_rep
            expected_ind += p_ind
            per_race_probs.append((p_dem, p_rep, p_ind))

        dem_win_probability, rep_win_probability = _independence_control_probabilities(
            per_race_probs, safe_dem_seats, safe_rep_seats
        )
        points.append(
            ChamberControlHistoryPoint(
                as_of=target_date,
                expected_dem_seats=expected_dem,
                expected_rep_seats=expected_rep,
                expected_independent_seats=expected_ind,
                dem_win_probability=dem_win_probability,
                rep_win_probability=rep_win_probability,
            )
        )

    # The most recent point is "right now" -- overwrite just its win
    # probabilities (not the expected-seats fields, which are exact
    # regardless of correlation, see module docstring) with the real
    # correlated joint simulation used everywhere else on the page
    # (simulate_chamber_control / the live /chamber-control/senate endpoint),
    # rather than the independence approximation every other point on this
    # trend line necessarily uses. Without this, the chart's own endpoint
    # visibly disagreed with the badges and home page showing the same
    # "today" -- the two numbers measure different things (independent vs.
    # correlated races) but a user has no way to know that just by comparing
    # them on the same page.
    if points:
        live = simulate_chamber_control(db, office=office)
        points[-1] = ChamberControlHistoryPoint(
            as_of=points[-1].as_of,
            expected_dem_seats=points[-1].expected_dem_seats,
            expected_rep_seats=points[-1].expected_rep_seats,
            expected_independent_seats=points[-1].expected_independent_seats,
            dem_win_probability=live.dem_win_probability,
            rep_win_probability=live.rep_win_probability,
        )

    return points
