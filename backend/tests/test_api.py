def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_races_lists_all_seeded_states(client):
    resp = client.get("/races")
    assert resp.status_code == 200
    codes = {r["state_code"] for r in resp.json()}
    assert codes == {"pa", "oh", "ga", "me", "ia"}


def test_unknown_state_returns_404(client):
    resp = client.get("/races/zz/polls")
    assert resp.status_code == 404


def test_polls_are_seeded_on_startup(client):
    resp = client.get("/races/pa/polls")
    assert resp.status_code == 200
    polls = resp.json()
    assert len(polls) == 9
    pollsters = {p["pollster"] for p in polls}
    assert "Quinnipiac University" in pollsters
    assert "Franklin & Marshall College" in pollsters
    assert "Susquehanna Polling & Research" in pollsters
    assert "PennLive" in pollsters
    assert "MAD Global Strategy" in pollsters


def test_polls_expose_normalized_weight(client):
    polls = client.get("/races/pa/polls").json()
    assert all(0 <= p["weight"] <= 1 for p in polls)
    assert abs(sum(p["weight"] for p in polls) - 1.0) < 1e-6

    # the most recent, largest poll shouldn't be out-weighed by a stale one
    by_date = sorted(polls, key=lambda p: p["field_end_date"])
    assert by_date[-1]["weight"] > 0


def test_forecast_is_generated_automatically_on_startup(client):
    resp = client.get("/races/pa/forecast")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_polls_used"] == 9
    assert len(body["results"]) == 2

    names = {r["candidate"]["name"] for r in body["results"]}
    assert names == {"Josh Shapiro", "Stacy Garrity"}

    shapiro = next(r for r in body["results"] if r["candidate"]["name"] == "Josh Shapiro")
    assert shapiro["win_probability"] > 0.9


def test_forecast_reports_polling_and_fundamentals_composition(client):
    body = client.get("/races/pa/forecast").json()

    assert 0 < body["poll_weight_alpha"] <= 1
    breakdown = body["fundamentals_breakdown"]
    for key in (
        "gubernatorial_lean_pts",
        "senate_lean_pts",
        "presidential_lean_pts",
        "combined_historical_lean_pts",
        "incumbency_pts",
        "registration_trend_pts",
        "national_environment_pts",
        "total_dem_margin_pts",
    ):
        assert key in breakdown

    shapiro = next(r for r in body["results"] if r["candidate"]["name"] == "Josh Shapiro")
    # Shapiro's structural advantages (incumbency, PA's Democratic lean, a
    # historically unpopular Republican president) should all point the same
    # way: a fundamentals-only estimate favoring him.
    assert shapiro["fundamentals_vote_share"] > 50
    assert shapiro["polling_vote_share"] > 50
    assert shapiro["mean_vote_share"] > 50


def test_forecast_history_includes_every_snapshot(client):
    client.post("/races/pa/simulate", json={"n_simulations": 500})
    client.post("/races/pa/simulate", json={"n_simulations": 500})

    resp = client.get("/races/pa/forecast/history")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["snapshots"]) == 3  # startup snapshot + 2 manual ones
    assert body["actuals"] == []
    assert body["election_date"] == "2026-11-03"
    # ascending order so the frontend can plot it directly as a time series
    timestamps = [s["created_at"] for s in body["snapshots"]]
    assert timestamps == sorted(timestamps)


def test_simulate_creates_a_new_snapshot(client):
    initial = client.get("/races/pa/forecast").json()

    resp = client.post("/races/pa/simulate", json={"n_simulations": 2000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_simulations"] == 2000
    assert body["id"] != initial["id"]

    forecast_resp = client.get("/races/pa/forecast")
    assert forecast_resp.status_code == 200
    assert forecast_resp.json()["id"] == body["id"]


def test_simulations_endpoint_returns_histograms(client):
    resp = client.get("/races/pa/simulations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["histograms"]) == 2
    for h in body["histograms"]:
        assert len(h["bin_edges"]) == 31
        assert len(h["counts"]) == 30
        assert len(h["draws_sample"]) > 0


def test_ohio_race_is_independently_seeded_and_forecast(client):
    polls = client.get("/races/oh/polls").json()
    assert len(polls) == 16
    pollster_names = {p["pollster"] for p in polls}
    assert "New York Times/Siena University" in pollster_names

    forecast = client.get("/races/oh/forecast").json()
    names = {r["candidate"]["name"] for r in forecast["results"]}
    assert names == {"Vivek Ramaswamy", "Amy Acton"}
    assert forecast["n_polls_used"] == 16


def test_georgia_race_is_independently_seeded_and_forecast(client):
    polls = client.get("/races/ga/polls").json()
    assert len(polls) == 4
    pollster_names = {p["pollster"] for p in polls}
    assert "Wick" in pollster_names

    forecast = client.get("/races/ga/forecast").json()
    names = {r["candidate"]["name"] for r in forecast["results"]}
    assert names == {"Rick Jackson", "Keisha Lance Bottoms"}
    assert forecast["n_polls_used"] == 4


def test_maine_race_is_independently_seeded_and_forecast(client):
    polls = client.get("/races/me/polls").json()
    assert len(polls) == 2
    pollster_names = {p["pollster"] for p in polls}
    assert "Fox News/Beacon Research/Shaw & Co. Research" in pollster_names

    forecast = client.get("/races/me/forecast").json()
    names = {r["candidate"]["name"] for r in forecast["results"]}
    assert names == {"Bobby Charles", "Hannah Pingree"}
    assert forecast["n_polls_used"] == 2

    pingree = next(r for r in forecast["results"] if r["candidate"]["name"] == "Hannah Pingree")
    assert pingree["win_probability"] > 0.5


def test_iowa_race_is_independently_seeded_and_forecast(client):
    polls = client.get("/races/ia/polls").json()
    assert len(polls) == 2
    pollster_names = {p["pollster"] for p in polls}
    assert "Siena College/New York Times" in pollster_names

    forecast = client.get("/races/ia/forecast").json()
    names = {r["candidate"]["name"] for r in forecast["results"]}
    assert names == {"Zach Lahn", "Rob Sand"}
    assert forecast["n_polls_used"] == 2

    # Sand leads both individual polls, but Iowa's fundamentals have leaned
    # solidly Republican since 2014 and still carry most of the blend this
    # far from Election Day, so the blended forecast favors Lahn overall.
    lahn = next(r for r in forecast["results"] if r["candidate"]["name"] == "Zach Lahn")
    assert lahn["win_probability"] > 0.5
    assert lahn["fundamentals_vote_share"] > 50
    sand = next(r for r in forecast["results"] if r["candidate"]["name"] == "Rob Sand")
    assert sand["polling_vote_share"] > 50


def test_all_five_forecasts_are_independent(client):
    pa = client.get("/races/pa/forecast").json()
    oh = client.get("/races/oh/forecast").json()
    ga = client.get("/races/ga/forecast").json()
    me = client.get("/races/me/forecast").json()
    ia = client.get("/races/ia/forecast").json()
    ids = {pa["id"], oh["id"], ga["id"], me["id"], ia["id"]}
    assert len(ids) == 5

    name_sets = [
        {r["candidate"]["name"] for r in race["results"]}
        for race in (pa, oh, ga, me, ia)
    ]
    for i, names_a in enumerate(name_sets):
        for names_b in name_sets[i + 1 :]:
            assert names_a.isdisjoint(names_b)
