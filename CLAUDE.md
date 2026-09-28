# Clash Analyzer

A personal progress and analytics app for Clash Royale, built on the official API. The FastAPI backend polls the API, stores snapshots and battles in SQLite, and computes analytics. The React frontend shows them on a dashboard.

## Hard rules

- **Never run `git commit` or `git push`** (and never `gh pr create`). The user handles version control. Read-only git commands are fine.
- **Keep `progress.md` current.** When a feature is done or the plan changes, update its checklist and version log. Bump the version in `backend/pyproject.toml` and `backend/src/clash_analyzer/__init__.py` together.
- **Never commit or echo secrets.** The API key lives only in `backend/.env`, which is gitignored. `backend/.env.example` holds placeholders. `/api/health` must never expose the key.
- **The API reference is `API_REFERENCE.md`.** Check a field there before using it. Many fields are optional or deprecated (`expLevel` is dead; use `kingTowerLevel` or `collectionLevel`).
- **Keep quality gates green:** backend `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`; frontend `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.

## Stack and layout

- **Backend (`backend/`):** Python 3.12, managed with **uv**, in a src layout at `backend/src/clash_analyzer/`.
  - `clash/`: the API client (`client.py`: cache, throttle, retry, typed errors) and `tags.py`
  - `domain/`: pure logic
    - `cards.py`: level normalization, Evo/Hero flags, upgrade cost table
    - `battles.py`: parse, winner detection, mode groups
    - `archetypes.py`
  - `services/`: `ingest`, `analytics`, `progress`, `upgrades`, `meta` (crawler and aggregation), `clans`
  - `routers/`: `players.py` and `general.py` (health, cards, clans, meta)
  - `models.py`: SQLModel tables. Datetimes are **naive UTC** (`NaiveDatetime`), and API output appends `Z`.
  - `scheduler.py`: APScheduler jobs (poll tracked players, meta crawl)
  - `main.py`: `create_app(settings, client)` factory
- **Tests (`backend/tests/`):**
  - `fixtures/` holds real API responses recorded 2026-09-28.
  - `conftest.py` provides `FakeAPI`, which plugs into `httpx.MockTransport` so the real client code runs, plus `raw_battle()` for synthetic battles.
- **Frontend (`frontend/`):** Vite, React 19, TypeScript strict, Tailwind v4, Recharts, TanStack Query, React Router.
  - `src/api/`: typed client, React Query hooks, response types
  - `src/components/`: `ui.tsx` primitives, `charts.tsx` (single-series only), `Layout.tsx`
  - `src/pages/`: page components; player tabs are in `pages/player/`, with `context.ts` for the player outlet context
  - `src/lib/`: format and tag helpers

## Conventions

**API calls**
- The base URL is `CR_API_BASE` (the official API, or `https://proxy.royaleapi.dev/v1` with IP `45.79.218.79` whitelisted). The key comes from `CR_API_KEY`.
- Tags: normalize (strip `#`, uppercase, `O` to `0`), validate against `[0289CGJLPQRUVY]`, and write `%23` in URLs. The backend and frontend implement the same rules.

**Game data**
- Card levels: `inGame = level + (16 - maxLevel)`.
- `evolutionLevel` is a bit flag: 1 = Evo, 2 = Hero.
- Battle winner: `boatBattleWon`, then opposite-sign `trophyChange`, then crowns, then unresolved.
- Mode groups: `trail` combined with `gameMode` Ladder means Seasonal Trophy Road (boosted levels). Keep it out of the ladder stats.
- Battle dedup key: `(player_tag, battleTime, opponent tags)`. Meta battles use a perspective-independent key over all tags.

**Analytics and charts**
- Every rate carries `games` and a Wilson CI.
- Insights require a sample of at least 5 (`MIN_SAMPLE`).
- Charts follow the dataviz rules:
  - one axis, one series color (`--series-1`)
  - status colors only with an icon or label
  - tokens live in `src/index.css` for light and dark
- Responsive grids need an explicit `grid-cols-1` base, and panels need `min-w-0`, or charts force horizontal overflow on phones.

## Commands

- **Backend:** `cd backend && uv run clash-analyzer` (127.0.0.1:8000, docs at `/docs`); tests with `uv run pytest --cov`.
- **Frontend:** `cd frontend && npm run dev` (localhost:5173, proxies `/api` to 8000).
- **Shell:** `python` is not on PATH on this machine. Use `uv run python` or `py`.
- **Screenshots:** headless Edge (`msedge --headless=new --screenshot`) works. Its minimum window width is about 500px, so narrower screenshots crop a wider layout.
