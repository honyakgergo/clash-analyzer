"""Database tables.

The API keeps no history: the battlelog rolls over after about 30 battles, and profiles only
show the current state. Everything here exists so we can build that history ourselves.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import NaiveDatetime
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# Everything is stored as naive UTC; API responses append "Z".


class Player(SQLModel, table=True):
    tag: str = Field(primary_key=True)
    name: str = ""
    tracked: bool = Field(default=False, index=True)
    clan_tag: str | None = None
    created_at: NaiveDatetime = Field(default_factory=utcnow)
    last_refreshed_at: NaiveDatetime | None = None
    last_snapshot_at: NaiveDatetime | None = None
    profile: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class PlayerSnapshot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    player_tag: str = Field(index=True, foreign_key="player.tag")
    taken_at: NaiveDatetime = Field(default_factory=utcnow, index=True)
    trophies: int = 0
    best_trophies: int = 0
    king_tower_level: int | None = None
    collection_level: int | None = None
    wins: int = 0
    losses: int = 0
    battle_count: int = 0
    three_crown_wins: int = 0
    pol_league: int | None = None
    pol_trophies: int | None = None
    pol_rank: int | None = None
    star_points: int | None = None
    total_donations: int | None = None
    mastery_levels: int = 0
    cards_owned: int = 0
    cards_maxed: int = 0
    avg_card_level: float | None = None


class Battle(SQLModel, table=True):
    id: str = Field(primary_key=True)
    player_tag: str = Field(index=True, foreign_key="player.tag")
    battle_time: NaiveDatetime = Field(index=True)
    type: str
    game_mode: str
    mode_group: str = Field(index=True)
    deck_selection: str | None = None
    arena: str | None = None
    league_number: int | None = None
    result: str
    crowns: int | None = None
    opp_crowns: int | None = None
    trophy_change: int | None = None
    starting_trophies: int | None = None
    king_hp: int | None = None
    princess_hp: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    opp_king_hp: int | None = None
    opp_princess_hp: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    elixir_leaked: float | None = None
    opp_elixir_leaked: float | None = None
    opp_tag: str | None = None
    opp_name: str | None = None
    opp_clan: str | None = None
    deck: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    opp_deck: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    avg_level: float | None = None
    opp_avg_level: float | None = None
    avg_elixir: float | None = None
    opp_avg_elixir: float | None = None
    evo_count: int = 0
    hero_count: int = 0
    opp_evo_count: int = 0
    opp_hero_count: int = 0
    archetype: str = ""
    opp_archetype: str = ""
    tower_troop: str | None = None
    event_tag: str | None = None
    ingested_at: NaiveDatetime = Field(default_factory=utcnow)


class MetaBattle(SQLModel, table=True):
    """One top-player battle, stored once no matter whose battlelog it came from."""

    id: str = Field(primary_key=True)
    battle_time: NaiveDatetime = Field(index=True)
    mode_group: str = Field(index=True)
    source_player: str
    result_a: str  # result from side A's perspective
    deck_a: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    deck_b: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    archetype_a: str = ""
    archetype_b: str = ""
    avg_elixir_a: float | None = None
    avg_elixir_b: float | None = None
    ingested_at: NaiveDatetime = Field(default_factory=utcnow)


class MetaCrawl(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    started_at: NaiveDatetime = Field(default_factory=utcnow)
    finished_at: NaiveDatetime | None = None
    status: str = "running"  # running / done / failed
    source: str = ""
    players_total: int = 0
    players_done: int = 0
    battles_added: int = 0
    error: str | None = None
