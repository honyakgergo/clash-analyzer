from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from .. import __version__
from ..clash.client import ClashClient
from ..deps import AppState, get_client, get_session, get_state
from ..scheduler import start_meta_crawl
from ..services import meta
from ..services.clans import clan_overview

router = APIRouter(prefix="/api", tags=["general"])


@router.get("/health")
def health(state: AppState = Depends(get_state)) -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "api_key_configured": bool(state.settings.cr_api_key.get_secret_value()),
        "api_base": state.settings.cr_api_base,
        "default_player_tag": state.settings.default_player_tag or None,
        "scheduler_enabled": state.settings.scheduler_enabled,
        "api_requests_made": state.client.requests_made,
    }


@router.get("/cards")
async def cards(client: ClashClient = Depends(get_client)) -> dict[str, Any]:
    return await client.cards()


@router.get("/clans/{tag}")
async def clan(tag: str, client: ClashClient = Depends(get_client)) -> dict[str, Any]:
    return await clan_overview(client, tag)


@router.get("/meta")
def meta_overview(
    session: Session = Depends(get_session),
    mode: str = Query("ranked"),
    days: int = Query(14, ge=1, le=90),
    min_deck_games: int = Query(3, ge=1),
) -> dict[str, Any]:
    return meta.meta_stats(session, mode, days, min_deck_games)


@router.get("/meta/status")
def meta_status(
    session: Session = Depends(get_session), state: AppState = Depends(get_state)
) -> dict[str, Any]:
    last = meta.latest_crawl(session)
    running = bool(state.meta_task and not state.meta_task.done())
    crawl = None
    if last:
        crawl = last.model_dump(mode="json")
        for key in ("started_at", "finished_at"):  # stored as naive UTC
            if crawl[key]:
                crawl[key] += "Z"
    return {"running": running, "last_crawl": crawl}


@router.post("/meta/refresh", status_code=202)
async def meta_refresh(state: AppState = Depends(get_state)) -> dict[str, Any]:
    started = start_meta_crawl(state)
    return {
        "started": started,
        "message": "Crawl started." if started else "A crawl is already running.",
    }
