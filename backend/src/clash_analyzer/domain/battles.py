"""Parse raw battlelog entries into flat, analysis-ready records.

The battlelog is written from the requesting player's point of view, but in 2v2 the
requesting player can be either ``team`` entry, so we look them up by tag.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .archetypes import classify_deck
from .cards import has_evo, has_hero, is_tower_troop, slim_card

MODE_GROUPS = (
    "ladder", "ranked", "seasonal", "war", "2v2", "tournament", "event", "friendly", "other",
)  # fmt: skip


def parse_battle_time(value: str) -> datetime:
    """``20260309T135844.000Z`` -> naive UTC datetime."""
    return datetime.strptime(value, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=UTC).replace(tzinfo=None)


def mode_group(battle: dict[str, Any]) -> str:
    btype = battle.get("type", "")
    mode = (battle.get("gameMode") or {}).get("name", "") or ""
    if len(battle.get("team") or []) > 1:
        return "2v2"
    if btype == "pathOfLegend":
        return "ranked"
    if btype == "PvP" and mode.startswith("Ladder"):
        return "ladder"
    if btype == "trail" and mode.startswith("Ladder"):
        return "seasonal"  # Seasonal Trophy Road: boosted levels, keep separate from ladder.
    if btype.startswith("riverRace") or btype == "boatBattle" or mode.startswith("CW_"):
        return "war"
    if btype == "tournament" or battle.get("isLadderTournament"):
        return "tournament"
    if btype in ("trail", "challenge", "PvP"):
        return "event"
    if btype in ("friendly", "clanMate", "clanMate2v2"):
        return "friendly"
    return "other"


def detect_result(battle: dict[str, Any], me: dict[str, Any], opp: dict[str, Any]) -> str:
    """``win`` / ``loss`` / ``draw`` / ``unknown`` following the documented precedence."""
    if "boatBattleWon" in battle:
        return "win" if battle["boatBattleWon"] else "loss"
    mine, theirs = me.get("trophyChange"), opp.get("trophyChange")
    if mine is not None and theirs is not None and (mine > 0) != (theirs > 0):
        return "win" if mine > 0 else "loss"
    a, b = me.get("crowns"), opp.get("crowns")
    if a is None or b is None:
        return "unknown"
    if a > b:
        return "win"
    if a < b:
        return "loss"
    return "draw"


def _deck(side: dict[str, Any]) -> list[dict[str, Any]]:
    return [slim_card(c) for c in side.get("cards") or [] if not is_tower_troop(c)]


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def _deck_stats(cards: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    levels = [c["level"] for c in cards if c.get("level") is not None]
    elixir = [c["elixir"] for c in cards if c.get("elixir") is not None]
    return _avg(levels), _avg(elixir)


def battle_key(player_tag: str, battle_time: str, opponent_tags: list[str]) -> str:
    raw = "|".join([player_tag, battle_time, *sorted(opponent_tags)])
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def match_key(battle_time: str, all_tags: list[str]) -> str:
    """Perspective-independent key, used to de-duplicate meta battles."""
    raw = "|".join([battle_time, *sorted(all_tags)])
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


@dataclass
class ParsedBattle:
    id: str
    player_tag: str
    battle_time: datetime
    type: str
    game_mode: str
    mode_group: str
    deck_selection: str | None
    arena: str | None
    league_number: int | None
    result: str
    crowns: int | None
    opp_crowns: int | None
    trophy_change: int | None
    starting_trophies: int | None
    king_hp: int | None
    princess_hp: list[int]
    opp_king_hp: int | None
    opp_princess_hp: list[int]
    elixir_leaked: float | None
    opp_elixir_leaked: float | None
    opp_tag: str | None
    opp_name: str | None
    opp_clan: str | None
    deck: list[dict[str, Any]]
    opp_deck: list[dict[str, Any]]
    avg_level: float | None
    opp_avg_level: float | None
    avg_elixir: float | None
    opp_avg_elixir: float | None
    evo_count: int
    hero_count: int
    opp_evo_count: int
    opp_hero_count: int
    archetype: str
    opp_archetype: str
    tower_troop: str | None
    event_tag: str | None

    @property
    def level_gap(self) -> float | None:
        if self.avg_level is None or self.opp_avg_level is None:
            return None
        return round(self.avg_level - self.opp_avg_level, 3)


def parse_battle(raw: dict[str, Any], player_tag: str) -> ParsedBattle:
    team = raw.get("team") or []
    opponents = raw.get("opponent") or []
    me = next((p for p in team if p.get("tag") == player_tag), team[0] if team else {})
    opp = opponents[0] if opponents else {}

    deck, opp_deck = _deck(me), _deck(opp)
    avg_level, avg_elixir = _deck_stats(deck)
    opp_avg_level, opp_avg_elixir = _deck_stats(opp_deck)
    my_cards = me.get("cards") or []
    opp_cards = opp.get("cards") or []
    support = (me.get("supportCards") or [None])[0]

    return ParsedBattle(
        id=battle_key(player_tag, raw["battleTime"], [o.get("tag", "") for o in opponents]),
        player_tag=player_tag,
        battle_time=parse_battle_time(raw["battleTime"]),
        type=raw.get("type", "unknown"),
        game_mode=(raw.get("gameMode") or {}).get("name", "") or "",
        mode_group=mode_group(raw),
        deck_selection=raw.get("deckSelection"),
        arena=(raw.get("arena") or {}).get("name"),
        league_number=raw.get("leagueNumber"),
        result=detect_result(raw, me, opp),
        crowns=me.get("crowns"),
        opp_crowns=opp.get("crowns"),
        trophy_change=me.get("trophyChange"),
        starting_trophies=me.get("startingTrophies"),
        king_hp=me.get("kingTowerHitPoints"),
        princess_hp=me.get("princessTowersHitPoints") or [],
        opp_king_hp=opp.get("kingTowerHitPoints"),
        opp_princess_hp=opp.get("princessTowersHitPoints") or [],
        elixir_leaked=me.get("elixirLeaked"),
        opp_elixir_leaked=opp.get("elixirLeaked"),
        opp_tag=opp.get("tag"),
        opp_name=opp.get("name"),
        opp_clan=(opp.get("clan") or {}).get("name"),
        deck=deck,
        opp_deck=opp_deck,
        avg_level=avg_level,
        opp_avg_level=opp_avg_level,
        avg_elixir=avg_elixir,
        opp_avg_elixir=opp_avg_elixir,
        evo_count=sum(has_evo(c.get("evolutionLevel")) for c in my_cards),
        hero_count=sum(has_hero(c.get("evolutionLevel")) for c in my_cards),
        opp_evo_count=sum(has_evo(c.get("evolutionLevel")) for c in opp_cards),
        opp_hero_count=sum(has_hero(c.get("evolutionLevel")) for c in opp_cards),
        archetype=classify_deck([c["id"] for c in deck], avg_elixir).name,
        opp_archetype=classify_deck([c["id"] for c in opp_deck], opp_avg_elixir).name,
        tower_troop=support.get("name") if support else None,
        event_tag=raw.get("eventTag") or raw.get("tournamentTag"),
    )
