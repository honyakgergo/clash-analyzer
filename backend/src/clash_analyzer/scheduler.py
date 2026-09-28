"""Background jobs: keep tracked players' history growing and the meta snapshot fresh."""

import asyncio
import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import select

from .clash.client import ClashAPIError
from .deps import AppState
from .models import Player, utcnow
from .services.ingest import refresh_player
from .services.meta import crawl_meta, latest_crawl

log = logging.getLogger(__name__)


async def poll_tracked_players(state: AppState) -> int:
    with state.session() as session:
        tags = session.exec(select(Player.tag).where(Player.tracked == True)).all()  # noqa: E712
    added = 0
    for tag in tags:
        try:
            with state.session() as session:
                result = await refresh_player(
                    session, state.client, tag, snapshot_interval=state.snapshot_interval
                )
            added += result.new_battles
        except ClashAPIError as exc:
            log.warning("poll %s failed: %s", tag, exc)
    log.info("polled %d tracked players, %d new battles", len(tags), added)
    return added


def start_meta_crawl(state: AppState) -> bool:
    """Start a crawl in the background unless one is already running."""
    if state.meta_task and not state.meta_task.done():
        return False
    state.meta_task = asyncio.create_task(
        crawl_meta(state.session, state.client, state.settings.meta_top_players)
    )
    return True


async def meta_job(state: AppState) -> None:
    with state.session() as session:
        last = latest_crawl(session)
    stale = timedelta(hours=state.settings.meta_refresh_hours)
    if last is None or last.status == "failed" or utcnow() - last.started_at >= stale:
        start_meta_crawl(state)


def build_scheduler(state: AppState) -> AsyncIOScheduler:
    s = state.settings
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        poll_tracked_players,
        "interval",
        minutes=s.battlelog_poll_minutes,
        args=[state],
        id="poll_tracked",
        next_run_time=utcnow() + timedelta(seconds=10),
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        meta_job,
        "interval",
        hours=1,
        args=[state],
        id="meta",
        next_run_time=utcnow() + timedelta(seconds=30),
        max_instances=1,
        coalesce=True,
    )
    return scheduler
