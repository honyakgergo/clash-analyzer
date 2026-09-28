import asyncio
from datetime import timedelta

from sqlmodel import Session, select

from clash_analyzer.deps import AppState
from clash_analyzer.models import Battle, MetaCrawl, Player
from clash_analyzer.scheduler import (
    build_scheduler,
    meta_job,
    poll_tracked_players,
    start_meta_crawl,
)

from .conftest import PLAYER_TAG


def _state(settings, engine, client) -> AppState:
    return AppState(settings=settings, engine=engine, client=client)


async def test_poll_only_tracked_players(settings, engine, client) -> None:
    state = _state(settings, engine, client)
    with Session(engine) as s:
        s.add(Player(tag=PLAYER_TAG, tracked=True))
        s.add(Player(tag="#CCCCCC", tracked=False))
        s.commit()
    assert await poll_tracked_players(state) == 30
    with Session(engine) as s:
        assert len(s.exec(select(Battle)).all()) == 30


async def test_poll_survives_api_errors(settings, engine, client) -> None:
    state = _state(settings, engine, client)
    with Session(engine) as s:
        s.add(Player(tag="#CCCCCC", tracked=True))  # not in the fake API -> 404
        s.commit()
    assert await poll_tracked_players(state) == 0


async def test_meta_job_starts_once_and_skips_when_fresh(settings, engine, client) -> None:
    state = _state(settings, engine, client)
    await meta_job(state)
    assert state.meta_task is not None
    assert start_meta_crawl(state) is False  # already running
    await state.meta_task
    first = state.meta_task
    await meta_job(state)  # fresh crawl exists -> no new task
    assert state.meta_task is first
    with Session(engine) as s:
        crawl = s.exec(select(MetaCrawl)).one()
        crawl.started_at -= timedelta(hours=settings.meta_refresh_hours + 1)
        s.add(crawl)
        s.commit()
    await meta_job(state)  # stale -> new crawl
    assert state.meta_task is not first
    await state.meta_task


async def test_build_scheduler_registers_jobs(settings, engine, client) -> None:
    scheduler = build_scheduler(_state(settings, engine, client))
    assert {j.id for j in scheduler.get_jobs()} == {"poll_tracked", "meta"}
    await asyncio.sleep(0)
