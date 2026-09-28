# Clash Royale API: Reference for clash_analyzer

Last compiled: 2026-09-28. The official spec is only visible after logging in at developer.clashroyale.com, so this is based on community docs checked against the live API ([jthingelstad/cr-agent-api-docs](https://github.com/jthingelstad/cr-agent-api-docs), updated 2026-09-26), the jcrapi2 changelog, and RoyaleAPI. Before relying on a field, check it against a real response.

## Basics

- **Base URL:** `https://api.clashroyale.com/v1`
- **Auth:** send `Authorization: Bearer <JWT>`. The key is tied to whitelisted IPs, and a wrong IP returns `403 accessDenied`.
- **No static IP?** Whitelist `45.79.218.79` and call `https://proxy.royaleapi.dev/v1/...` instead.
- **Tags:** only the characters `0289CGJLPQRUVY`, uppercase. The `#` must be written as `%23`. Users often type the letter `O` when they mean the digit `0`.
- **Rate limits:** set per IP. Going over can return a 403 instead of a 429, and there are no rate-limit headers. Keep requests about 1–2 s apart and cache responses.
- **Cache:** `cache-control: max-age` is about 60 s for players and about 120 s for clans. Polling faster than that returns the same data.
- **Dates:** `20260309T135844.000Z`, i.e. `YYYYMMDDTHHmmss.sssZ`.
- **Pagination:** `limit`, then `after` or `before` (not both). The response is `{items, paging:{cursors}}`, and an empty `cursors` means there are no more pages.
- **Missing fields:** optional fields are usually left out rather than set to `null`, so check whether the key exists.

## Endpoints

| Status | Method | Path | Notes |
|---|---|---|---|
| ✅ | GET | `/players/{tag}` | Full profile. See Player below. |
| ✅ | GET | `/players/{tag}/battlelog` | Bare array of about the last 30 battles. **Old battles roll off, so poll and store them.** |
| ✅ | GET | `/players/{tag}/upcomingchests` | `{items:[{index,name}]}`. Only notable chests are listed. How useful it still is after the reward rework is unclear. |
| 🔒 | POST | `/players/{tag}/verifytoken` | Checks an in-game API token. Needs a special scope. |
| ✅ | GET | `/clans?name=&locationId=&minMembers=&maxMembers=&minScore=` | Search. Needs at least one filter, and `name` must be at least 3 characters. |
| ✅ | GET | `/clans/{tag}` | Clan info and `memberList`: role, `lastSeen`, trophies, donations, rank. |
| ✅ | GET | `/clans/{tag}/members` | Paginated members. |
| ✅ | GET | `/clans/{tag}/currentriverrace` | Live war with each participant's `fame`, `decksUsed`, `decksUsedToday`, `boatAttacks`. Returns 404 for a short gap at season rollover. |
| ✅ | GET | `/clans/{tag}/riverracelog` | Past war weeks with standings and participants. |
| ❌ | GET | `/clans/{tag}/warlog` | Returns 404 ("temporarily disabled"). |
| ❌ | GET | `/clans/{tag}/currentwar` | Returns 410 (gone). |
| ✅ | GET | `/cards` | `{items (123 cards), supportItems (4 tower troops)}`. Ignores paging. |
| ✅ | GET | `/tournaments?name=` | Search. Appears to return only active tournaments. |
| ✅ | GET | `/tournaments/{tag}` | Details plus `membersList` (score, rank). |
| ⚠️ | GET | `/globaltournaments` | Often empty. |
| ✅ | GET | `/locations` / `/locations/{id}` | 262 locations with IDs 5700xxxx. Use `global` for worldwide. |
| ⚠️ | GET | `/locations/{id}/rankings/players` | Trophy leaderboard. Was returning empty in 2026. |
| ✅ | GET | `/locations/{id}/rankings/clans` | Capped at 1,000. |
| ✅ | GET | `/locations/{id}/rankings/clanwars` | Capped at 1,000. |
| ✅ | GET | `/locations/{id}/pathoflegend/players` | Current Ranked board with `eloRating`. Capped at 1,000. |
| ✅ | GET | `/locations/global/pathoflegend/{seasonId}/rankings/players` | Past Ranked season final standings, up to 9,999 deep, from 2022-10 onward. |
| ✅ | GET | `/locations/global/seasons` | List of season IDs (`YYYY-MM`). |
| ❌ | GET | `/locations/global/seasonsV2` | Every field is null. |
| ❌ | GET | `/locations/global/seasons/{id}/rankings/players` | Returns notFound. |
| ✅ | GET | `/locations/global/rankings/tournaments/{tag}` | Global tournament standings. |
| ✅ | GET | `/leaderboards` / `/leaderboard/{id}` | Game-mode boards such as Merge Tactics and 2v2 League: `{rank, score}`. |
| ✅ | GET | `/events` | `{eventTag, title, description}`. Connects to `battle.eventTag`. |
| ❌ | GET | `/challenges` | Returns notFound. |

## Player object (`/players/{tag}`)

**Progression**
- `trophies`, `bestTrophies` (Trophy Road now caps at 14,000)
- `arena`
- `legacyTrophyRoadHighScore` (the high before the 2025 rework; can be null)
- `kingTowerLevel` (new in 2026-09)
- `collectionLevel` (new: the sum of card levels plus 5 for each Evo/Hero)
- `starPoints`
- `expLevel`, `expPoints`, `totalExpPoints`: **deprecated in 2026**

**Record**
- `wins`, `losses`, `battleCount`, `threeCrownWins`
- `currentWinLoseStreak` (signed: positive for a win streak, negative for a loss streak)
- `challengeCardsWon`, `challengeMaxWins`
- `tournamentCardsWon`, `tournamentBattleCount`

**Social**
- `donations`, `donationsReceived` (this season), `totalDonations` (lifetime)
- `clan{tag,name,badgeId}` and `role`: both left out if the player has no clan
- `warDayWins`, `clanCardsCollected`

**Seasons**
- `leagueStatistics.{currentSeason, previousSeason, bestSeason}`, each with trophies and rank
- `current|last|bestPathOfLegendSeasonResult {leagueNumber, trophies (=rating), rank}`, or null

**Cards**
- `cards[]` is the full collection. `currentDeck[]` holds 8 cards and can be stale, because it only updates after a battle. `supportCards[]` and `currentDeckSupportCards[]` are tower troops.
- Each card has `name`, `id`, `level`, `maxLevel`, `rarity`, `count` (copies held), `elixirCost`, `starLevel`, `evolutionLevel`, `maxEvolutionLevel`, and `iconUrls{medium, evolutionMedium, heroMedium}`.
- `currentFavouriteCard`

**Badges and achievements**
- `badges[]` has `{name, level, maxLevel, progress, target}`. It includes **card mastery** (`Mastery<Card>`), `YearsPlayed` (progress is in days), and `CollectionLevel`.
- `achievements[]`: 12 fixed achievements with `{stars, value, target}`.

**Other modes**
- `progress{}` maps each mode-season (Merge Tactics, seasonal trophy road, 2v2 League…) to `{arena, trophies, bestTrophies}`. Treat the keys as opaque.

### Card level conversion (important)

The API reports levels relative to rarity. To get the in-game level:

```
inGameLevel = level + (16 - maxLevel)
```

| Rarity | API maxLevel |
|---|---|
| common | 16 |
| rare | 14 |
| epic | 11 |
| legendary | 8 |
| champion | 6 |

`evolutionLevel` and `maxEvolutionLevel` are **bit flags**, not levels: `1` = Evo, `2` = Hero, `3` = both. In `cards[]` they mean the player owns that form, in `currentDeck` the form is slotted, and in battles it was played.

The API does not return upgrade costs, so gold and card copies still needed have to come from a hardcoded table taken from the wiki.

## Battle object (`/battlelog`)

**Battle-level fields**
- `type`: `PvP`, `pathOfLegend`, `trail`, `clanMate`, `friendly`, `riverRacePvP`, `riverRaceDuel`, `riverRaceDuelColosseum`, `tournament`, `boatBattle` and others. Since June 2026, `trail` combined with `gameMode` Ladder means Seasonal Trophy Road, where levels are boosted. Don't mix those battles with ladder stats.
- `battleTime`, `gameMode{id,name}`, `arena`, `deckSelection`, `leagueNumber`
- `isLadderTournament`, `isHostedMatch`, `tournamentTag`, `eventTag`
- `modifiers` (only in CHAOS modes)
- Boat battles only: `boatBattleSide`, `boatBattleWon`, `newTowersDestroyed`, `prevTowersDestroyed`, `remainingTowers`

**`team[]` / `opponent[]`** (2 entries each in 2v2)
- `tag`, `name`, `clan`, `globalRank`
- `crowns`: summed over games in duels
- `startingTrophies`, `trophyChange`: often left out; see the notes below
- `kingTowerHitPoints`, `princessTowersHitPoints[]` (destroyed towers are left out)
- `elixirLeaked`
- `cards[]` with the levels and evo/hero form used in that battle, and `supportCards[]`
- `rounds[]` in duels: per-round crowns, HP, leaked elixir, and cards with a `used` flag

**There is no winner field.** Work it out in this order:
1. `boatBattleWon`
2. `trophyChange`, if the two sides moved in opposite directions (in a Path of Legends draw, both sides lose rating)
3. Compare crowns
4. Otherwise unresolved

**`trophyChange` quirks**
- In Path of Legends leagues 1–6 it only appears on wins.
- A loss at an arena floor has no `trophyChange`.
