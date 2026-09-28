from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, col, select

from ..clash.client import ClashClient
from ..clash.tags import normalize_tag
from ..deps import AppState, get_client, get_session, get_state
from ..domain.cards import MAX_LEVEL
from ..models import Battle, Player, PlayerSnapshot
from ..services import analytics, meta, progress, upgrades
from ..services.ingest import refresh_player

router = APIRouter(prefix="/api/players", tags=["players"])


async def load_player(
    tag: str,
    session: Session = Depends(get_session),
    client: ClashClient = Depends(get_client),
    state: AppState = Depends(get_state),
) -> Player:
    """Return the stored player, refreshing it from the API if missing or stale."""
    tag = normalize_tag(tag)
    await refresh_player(
        session,
        client,
        tag,
        snapshot_interval=state.snapshot_interval,
        min_refresh_interval=timedelta(seconds=state.settings.auto_refresh_seconds),
    )
    player = session.get(Player, tag)
    assert player is not None and player.profile is not None
    return player


def _meta(session: Session, player: Player) -> dict[str, Any]:
    battles = session.exec(
        select(func.count()).select_from(Battle).where(Battle.player_tag == player.tag)
    ).one()
    snapshots = session.exec(
        select(func.count())
        .select_from(PlayerSnapshot)
        .where(PlayerSnapshot.player_tag == player.tag)
    ).one()
    return {
        "tracked": player.tracked,
        "last_refreshed_at": player.last_refreshed_at.isoformat() + "Z"
        if player.last_refreshed_at
        else None,
        "battles_stored": battles,
        "snapshots_stored": snapshots,
    }


@router.get("/tracked")
def tracked_players(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    players = session.exec(select(Player).where(Player.tracked == True)).all()  # noqa: E712
    return [
        {
            "tag": p.tag,
            "name": p.name,
            "trophies": (p.profile or {}).get("trophies"),
            "last_refreshed_at": p.last_refreshed_at.isoformat() + "Z"
            if p.last_refreshed_at
            else None,
        }
        for p in players
    ]


@router.get("/{tag}")
def get_player(
    player: Player = Depends(load_player), session: Session = Depends(get_session)
) -> dict[str, Any]:
    assert player.profile is not None
    return {"summary": progress.profile_summary(player.profile), **_meta(session, player)}


@router.post("/{tag}/refresh")
async def force_refresh(
    tag: str,
    session: Session = Depends(get_session),
    client: ClashClient = Depends(get_client),
    state: AppState = Depends(get_state),
) -> dict[str, Any]:
    result = await refresh_player(session, client, tag, snapshot_interval=state.snapshot_interval)
    return {
        "tag": result.tag,
        "new_battles": result.new_battles,
        "snapshot_taken": result.snapshot_taken,
    }


@router.post("/{tag}/track")
def track(
    player: Player = Depends(load_player), session: Session = Depends(get_session)
) -> dict[str, Any]:
    player.tracked = True
    session.add(player)
    session.commit()
    return {"tag": player.tag, "tracked": True}


@router.delete("/{tag}/track")
def untrack(
    player: Player = Depends(load_player), session: Session = Depends(get_session)
) -> dict[str, Any]:
    player.tracked = False
    session.add(player)
    session.commit()
    return {"tag": player.tag, "tracked": False}


@router.get("/{tag}/battles")
def battles(
    player: Player = Depends(load_player),
    session: Session = Depends(get_session),
    mode: str = Query("all"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    query = select(Battle).where(Battle.player_tag == player.tag)
    groups = analytics.MODE_FILTERS.get(mode)
    if groups:
        query = query.where(col(Battle.mode_group).in_(groups))
    rows = session.exec(
        query.order_by(col(Battle.battle_time).desc()).offset(offset).limit(limit)
    ).all()
    return {
        "items": [
            {
                **b.model_dump(exclude={"ingested_at"}),
                "battle_time": b.battle_time.isoformat() + "Z",
            }
            for b in rows
        ],
        "offset": offset,
        "limit": limit,
    }


@router.get("/{tag}/progress")
def player_progress(
    player: Player = Depends(load_player), session: Session = Depends(get_session)
) -> dict[str, Any]:
    return progress.progress_timeseries(session, player.tag)


@router.get("/{tag}/collection")
def player_collection(player: Player = Depends(load_player)) -> list[dict[str, Any]]:
    assert player.profile is not None
    return progress.collection(player.profile)


@router.get("/{tag}/mastery")
async def player_mastery(
    player: Player = Depends(load_player), client: ClashClient = Depends(get_client)
) -> dict[str, Any]:
    assert player.profile is not None
    catalog = (await client.cards()).get("items", [])
    return progress.mastery_overview(player.profile, catalog)


@router.get("/{tag}/upgrades")
def player_upgrades(
    player: Player = Depends(load_player),
    session: Session = Depends(get_session),
    target_level: int = Query(MAX_LEVEL, ge=1, le=MAX_LEVEL),
) -> dict[str, Any]:
    assert player.profile is not None
    return upgrades.upgrade_plan(session, player.profile, target_level)


@router.get("/{tag}/analytics")
def player_analytics(
    player: Player = Depends(load_player),
    session: Session = Depends(get_session),
    mode: str = Query("competitive"),
    days: int | None = Query(None, ge=1, le=3650),
    tz: str | None = Query(None, description="IANA timezone, e.g. Europe/Amsterdam"),
) -> dict[str, Any]:
    return analytics.analytics_report(session, player.tag, mode, days, tz)


@router.get("/{tag}/chests")
async def player_chests(
    tag: str, client: ClashClient = Depends(get_client)
) -> list[dict[str, Any]]:
    return await client.upcoming_chests(normalize_tag(tag))


@router.get("/{tag}/meta-compare")
def player_meta_compare(
    player: Player = Depends(load_player),
    session: Session = Depends(get_session),
    mode: str = Query("ranked"),
    days: int = Query(14, ge=1, le=90),
) -> dict[str, Any]:
    assert player.profile is not None
    deck = progress.profile_summary(player.profile)["current_deck"]
    return meta.compare_deck(session, deck, mode, days)
