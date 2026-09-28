"""Shared application state and FastAPI dependencies."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlmodel import Session

from .clash.client import ClashClient
from .config import Settings


@dataclass
class AppState:
    settings: Settings
    engine: Engine
    client: ClashClient
    meta_task: asyncio.Task | None = None

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine) as session:
            yield session

    @property
    def snapshot_interval(self) -> timedelta:
        return timedelta(minutes=self.settings.snapshot_min_interval_minutes)


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def get_session(state: AppState = Depends(get_state)) -> Iterator[Session]:
    with Session(state.engine) as session:
        yield session


def get_client(state: AppState = Depends(get_state)) -> ClashClient:
    return state.client
