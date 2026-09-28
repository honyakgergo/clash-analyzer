# Progress

Status legend: ✅ done · 🚧 in progress · ⬜ planned · ❌ dropped

## Current version: **v0.5.2** (2026-09-28)

| Metric | Value |
|---|---|
| Backend tests | 112 passing, 95% coverage |
| Frontend tests | 22 passing |
| Lint / format / typecheck | ruff ✓ · oxlint ✓ · tsc strict ✓ |
| Live-verified against real API | ✓ (player #PQGGV0JP, clan #Q8RPVJ2P, top-100 Ranked crawl) |

## Version log

| Version | Date | Summary |
|---|---|---|
| v0.0 | 2026-09-28 | Research: API reference, CLAUDE.md, plan |
| v0.1 | 2026-09-28 | Backend foundation: uv project, async API client (cache/throttle/retry), SQLite models, ingestion with dedup, scheduler |
| v0.2 | 2026-09-28 | Progress tracker: snapshots, trophy path, deltas, mastery/badges/achievements |
| v0.3 | 2026-09-28 | Upgrade planner: verified Level-16 cost table, deck readiness, upgrade-next ranking |
| v0.4 | 2026-09-28 | Battle analytics: tilt, sessions, level gap, elixir, close games, evo/hero, matchups, archetypes, insights |
| v0.5 | 2026-09-28 | Meta crawler and comparison, clan page, full React frontend (light/dark, responsive), docs |
| v0.5.1 | 2026-09-28 | Launcher: clear "port already in use" message instead of a traceback, `--port` option |
| v0.5.2 | 2026-09-28 | Theme: two-mode light/dark toggle (the confusing "system" option is removed); first visit follows the OS; no flash on load |

## Milestones

### v0.1: Backend foundation ✅
- ✅ uv project (src layout), `.env` / `.env.example`, `.gitignore`
- ✅ Async API client: auth, tag normalization, TTL cache (max-age), throttle, retry/backoff, typed errors
- ✅ SQLite models: Player, PlayerSnapshot, Battle, MetaBattle, MetaCrawl
- ✅ Ingestion: profile, snapshot (at most hourly), deduplicated battles
- ✅ Scheduler: poll tracked players every 15 min, meta crawl daily
- ✅ Tests with recorded real fixtures

### v0.2: Progress tracker ✅
- ✅ Trophy path from battles, snapshot trends, day/week/month deltas
- ✅ Mastery badges mapped to cards (with internal-name aliases), closest-to-next, achievements, badges
- ✅ Frontend: search, profile header, overview, progress charts

### v0.3: Upgrade planner ✅
- ✅ Cost table (post Nov 2025), verified against published totals in tests
- ✅ Deck readiness to a target level 13–16, gold and copies missing, levels affordable
- ✅ Upgrade next (played cards, enough copies, cheapest), almost-there, collection browser

### v0.4: Battle analytics ✅
- ✅ Win rate with Wilson CI, by mode, hour, weekday, day
- ✅ Tilt: after win/loss/2+ losses/3+ wins, streaks, sessions and fatigue by game index
- ✅ Level gap buckets and share of losses where you were underleveled
- ✅ Tower HP close-game analysis, elixir leaked buckets
- ✅ Evo and Hero impact and special-form advantage
- ✅ Nemesis/prey cards, opponent archetypes, your decks, card and tower troop performance
- ✅ Rule-based plain-English insights

### v0.5: Meta comparison ✅
- ✅ Crawl the top Ranked players' battlelogs (falls back to last season early in a season)
- ✅ Card usage/win rate/evo rate, archetypes, top decks
- ✅ Your deck vs meta: per-card stats, similar decks, swap ideas, off-meta cards
- ✅ Clan page: members, inactivity, river race standings, decks used today

### v0.6: Polish (next)
- ⬜ Screenshots in the README
- ⬜ Docker Compose (backend + built frontend)
- ⬜ Deploy notes (static IP or RoyaleAPI proxy)
- ⬜ Re-classify stored archetypes when the rules change (labels are computed at ingest)
- ⬜ Card-level "vs opponents" per rarity, not just the deck average
- ⬜ Optional: CSV export of stored battles

## Known limitations
- The API exposes no replays or placement coordinates, so positional analysis is impossible.
- Upgrade costs and wild cards are not in the API. The cost table is hardcoded, and "can upgrade" checks copies only.
- Path of Legends `trophyChange` is missing on losses in leagues 1–6, so the ranked trophy path is partial.
- `/locations/{id}/rankings/players` (the trophy leaderboard) is often empty. The meta uses the Path of Legends board.
