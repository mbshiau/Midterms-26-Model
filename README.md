# 2026 Midterms Forecast

A full-stack election forecasting model for the 2026 U.S. midterms — every Senate race, every gubernatorial race, and all 435 House districts. Combines real polling averages with a fundamentals model (historical partisan lean, incumbency, national environment) into a Monte Carlo simulation, refreshed twice daily from live sources.

Built with FastAPI + PostgreSQL on the backend and React + TypeScript on the frontend.

## How the model works

Each race's forecast blends two independent estimates, weighted by how close the race is to Election Day:

- **Polling average** — real polls only, scraped from each race's Wikipedia page (national House/Senate/Governor pages, or a state's own page when it publishes real per-district tables). Weighted by recency and pollster quality; never fabricated or interpolated. A race with zero real polls is forecast on fundamentals alone rather than guessing at a number.
- **Fundamentals model** — a state/district's historical partisan lean (past Governor/Senate/presidential results for statewide races, Cook PVI + prior House results for districts), incumbency advantage, and a national-environment adjustment derived from presidential approval and the generic congressional ballot.

The blend is run through a Monte Carlo simulation (10,000 draws by default) that shares a single correlated "national polling error" shock across every race generated on the same day, so a systematic miss moves every state together rather than drawing fully independent noise per race. Senate/House chamber-control odds are computed the same way, aggregating all individual-race simulations into a joint seat-count distribution.

A standalone section surfaces Kalshi prediction-market odds for comparison — display-only, never blended into the model itself.

## Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, NumPy/pandas for simulation, APScheduler for the twice-daily refresh job
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Recharts
- **Data ingestion**: BeautifulSoup scrapers against Wikipedia's MediaWiki API (polls, candidates, PVI, redistricting status) and Kalshi's market API
- **Deployment**: Render (backend + Postgres), Vercel (frontend), with a GitHub Actions cron job keeping Render's free-tier instance from sleeping through a scheduled refresh

## Running locally

The easiest path is Docker Compose, which starts Postgres and the backend together:

```bash
docker compose up -d --build
```

The backend seeds its database and starts serving at `http://localhost:8000` (interactive API docs at `/docs`). On first boot it seeds every race, scrapes whatever real polls are currently available, and generates an initial forecast for each one.

In a separate terminal, run the frontend:

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies API requests to the backend.

### Without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # point DATABASE_URL at your own Postgres instance
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Configuration

Copy `backend/.env.example` to `backend/.env` to override defaults or add optional integrations:

- **Kalshi** — real prediction-market odds for the display-only markets section. Requires an API key ID and a private key file (never committed; goes in the gitignored `backend/secrets/`).
- **UF Navigator** (or any OpenAI-compatible endpoint) — powers the Race Intelligence section's AI news summaries. Left blank, that section's AI text just doesn't populate rather than erroring.

Everything else (simulation count, error terms, recency half-life, CORS origins) has a reasonable default and only needs overriding for local experimentation.

## Tests

```bash
cd backend
python -m pytest
```

## Project layout

```
backend/
  app/
    routers/        # FastAPI route handlers
    services/        # forecasting, simulation, chamber control, fundamentals model
    ingestion/        # Wikipedia/Kalshi scrapers + the scheduled refresh job
    seed/             # per-race candidate/district seed data
    data/              # fundamentals inputs (historical elections, PVI, model overrides)
  scripts/           # one-off backfill/generation scripts
  tests/
frontend/
  src/
    pages/           # route-level pages (home, state detail, House/Senate/Governor maps)
    components/      # charts, maps, and shared UI
    api/              # typed API client
```

## Data integrity

Every number in this model traces back to a real, cited source — Wikipedia's own polling tables, election results, and PVI figures, or Kalshi's live market data. Nothing is interpolated or invented: a race with no real polls yet is shown as fundamentals-only rather than backfilled with a plausible-looking number, and an unparseable data point is skipped and logged rather than guessed at.
