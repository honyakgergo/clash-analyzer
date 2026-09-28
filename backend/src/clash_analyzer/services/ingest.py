"""Fetch a player's profile and battlelog from the API and store them."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlmodel import Session, col, select

from ..clash.client import ClashClient
from ..clash.tags import normalize_tag
from ..domain.battles import parse_battle
from ..domain.cards import MAX_LEVEL, card_level
from ..models import Battle, Player, PlayerSnapshot, utcnow


@dataclass
class RefreshResult:
    tag: str
    new_battles: int
    snapshot_taken: bool
    skipped: bool = False


def snapshot_from_profile(profile: dict[str, Any]) -> PlayerSnapshot:
    cards = profile.get("cards") or []
    levels = [card_level(c) for c in cards]
    pol = profile.get("currentPathOfLegendSeasonResult") or {}
    mastery = [b for b in profile.get("badges") or [] if b.get("name", "").startswith("Mastery")]
    return PlayerSnapshot(
        player_tag=profile["tag"],
        trophies=profile.get("trophies", 0),
        best_trophies=profile.get("bestTrophies", 0),
        king_tower_level=profile.get("kingTowerLevel"),
        collection_level=profile.get("collectionLevel"),
        wins=profile.get("wins", 0),
        losses=profile.get("losses", 0),
        battle_count=profile.get("battleCount", 0),
        three_crown_wins=profile.get("threeCrownWins", 0),
        pol_league=pol.get("leagueNumber"),
        pol_trophies=pol.get("trophies"),
        pol_rank=pol.get("rank"),
        star_points=profile.get("starPoints"),
        total_donations=profile.get("totalDonations"),
        mastery_levels=sum(b.get("level", 0) for b in mastery),
        cards_owned=len(cards),
        cards_maxed=sum(lvl >= MAX_LEVEL for lvl in levels),
        avg_card_level=round(sum(levels) / len(levels), 3) if levels else None,
    )


def upsert_player(
    session: Session, profile: dict[str, Any], *, tracked: bool | None = None
) -> Player:
    player = session.get(Player, profile["tag"]) or Player(tag=profile["tag"])
    player.name = profile.get("name", player.name)
    player.clan_tag = (profile.get("clan") or {}).get("tag")
    player.profile = profile
    if tracked is not None:
        player.tracked = tracked
    session.add(player)
    return player


def store_battles(session: Session, player_tag: str, raw_battles: list[dict[str, Any]]) -> int:
    parsed = [parse_battle(b, player_tag) for b in raw_battles if b.get("battleTime")]
    if not parsed:
        return 0
    ids = [p.id for p in parsed]
    existing = set(session.exec(select(Battle.id).where(col(Battle.id).in_(ids))).all())
    added = 0
    for p in parsed:
        if p.id in existing:
            continue
        session.add(Battle(**vars(p)))
        existing.add(p.id)
        added += 1
    return added


async def refresh_player(
    session: Session,
    client: ClashClient,
    tag: str,
    *,
    snapshot_interval: timedelta = timedelta(hours=1),
    min_refresh_interval: timedelta | None = None,
) -> RefreshResult:
    tag = normalize_tag(tag)
    player = session.get(Player, tag)
    now = utcnow()
    if (
        min_refresh_interval is not None
        and player is not None
        and player.last_refreshed_at is not None
        and now - player.last_refreshed_at < min_refresh_interval
    ):
        return RefreshResult(tag, 0, False, skipped=True)

    profile, battles = await asyncio.gather(client.player(tag), client.battlelog(tag))
    player = upsert_player(session, profile)
    player.last_refreshed_at = now
    session.flush()

    snapshot_taken = False
    if player.last_snapshot_at is None or now - player.last_snapshot_at >= snapshot_interval:
        session.add(snapshot_from_profile(profile))
        player.last_snapshot_at = now
        snapshot_taken = True

    added = store_battles(session, tag, battles)
    session.commit()
    return RefreshResult(tag, added, snapshot_taken)
