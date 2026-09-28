"""Shared fixtures.

``tests/fixtures`` holds real API responses (recorded 2026-09-28) so parsing is tested
against the actual payload shape. The HTTP layer is replaced by ``httpx.MockTransport``, so
the real ``ClashClient`` code, including caching, retries and error mapping, still runs.
"""

import json
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session

from clash_analyzer.clash.client import ClashClient
from clash_analyzer.config import Settings
from clash_analyzer.db import init_db, make_engine
from clash_analyzer.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
PLAYER_TAG = "#PQGGV0JP"
CLAN_TAG = "#Q8RPVJ2P"


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


Routes = dict[str, tuple[int, Any] | Callable[[httpx.Request], httpx.Response]]


def default_routes() -> Routes:
    top = load("pathoflegend")
    top_tag = top["items"][0]["tag"]
    return {
        f"/v1/players/{PLAYER_TAG}": (200, load("player")),
        f"/v1/players/{PLAYER_TAG}/battlelog": (200, load("battlelog")),
        f"/v1/players/{PLAYER_TAG}/upcomingchests": (200, load("upcomingchests")),
        "/v1/cards": (200, load("cards")),
        f"/v1/clans/{CLAN_TAG}": (200, load("clan")),
        f"/v1/clans/{CLAN_TAG}/currentriverrace": (200, load("currentriverrace")),
        "/v1/locations/global/pathoflegend/players": (200, top),
        f"/v1/players/{top_tag}/battlelog": (200, load("battlelog_top")),
    }


class FakeAPI:
    """Routes requests by decoded path; records calls for assertions."""

    def __init__(self, routes: Routes | None = None) -> None:
        self.routes = routes if routes is not None else default_routes()
        self.calls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path  # httpx decodes %23 -> #
        self.calls.append(path)
        route = self.routes.get(path)
        if route is None:
            return httpx.Response(404, json={"reason": "notFound"})
        if callable(route):
            return route(request)
        status, body = route
        return httpx.Response(status, json=body, headers={"cache-control": "max-age=60"})


@pytest.fixture
def fake_api() -> FakeAPI:
    return FakeAPI()


@pytest.fixture
def make_client() -> Iterator[Callable[[FakeAPI], ClashClient]]:
    clients: list[ClashClient] = []

    def _make(api: FakeAPI, **kwargs: Any) -> ClashClient:
        client = ClashClient(
            "test-key",
            "https://api.test/v1",
            min_interval_s=0,
            transport=httpx.MockTransport(api),
            **kwargs,
        )
        clients.append(client)
        return client

    yield _make


@pytest.fixture
def client(fake_api: FakeAPI, make_client: Callable[..., ClashClient]) -> ClashClient:
    return make_client(fake_api)


@pytest.fixture
def engine() -> Engine:
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


@pytest.fixture
def settings() -> Settings:
    return Settings(
        cr_api_key="test-key",  # type: ignore[arg-type]
        cr_api_base="https://api.test/v1",
        database_url="sqlite://",
        scheduler_enabled=False,
        min_request_interval_s=0,
        meta_top_players=3,
    )


@pytest.fixture
def api(settings: Settings, client: ClashClient) -> Iterator[TestClient]:
    with TestClient(create_app(settings, client=client)) as tc:
        yield tc


# -- synthetic battles ------------------------------------------------------------------------

BASE_TIME = datetime(2026, 9, 1, 12, 0, 0)


def card(
    cid: int, name: str, level: int = 14, max_level: int = 16, elixir: int = 3, **extra: Any
) -> dict:
    return {
        "id": cid,
        "name": name,
        "level": level,
        "maxLevel": max_level,
        "rarity": "common",
        "elixirCost": elixir,
        "iconUrls": {"medium": f"https://img/{cid}.png"},
        **extra,
    }


DEFAULT_DECK = [card(26000021 + i * 1000, f"Card{i}", elixir=3) for i in range(8)]
OPP_DECK = [card(26000009, "Golem", elixir=8)] + [card(26100000 + i, f"Opp{i}") for i in range(7)]


def raw_battle(
    minutes: float = 0,
    crowns: int = 1,
    opp_crowns: int = 0,
    *,
    btype: str = "PvP",
    mode: str = "Ladder",
    my_level: int = 14,
    opp_level: int = 14,
    trophy_change: int | None = None,
    opp_trophy_change: int | None = None,
    leaked: float = 1.0,
    opp_tag: str = "#OPP0",
    my_cards: list[dict] | None = None,
    opp_cards: list[dict] | None = None,
    **extra: Any,
) -> dict:
    t = BASE_TIME + timedelta(minutes=minutes)
    me: dict[str, Any] = {
        "tag": PLAYER_TAG,
        "name": "Me",
        "crowns": crowns,
        "kingTowerHitPoints": 5000,
        "princessTowersHitPoints": [3000],
        "elixirLeaked": leaked,
        "cards": [{**c, "level": my_level} for c in (my_cards or DEFAULT_DECK)],
    }
    opp: dict[str, Any] = {
        "tag": opp_tag,
        "name": "Opp",
        "crowns": opp_crowns,
        "kingTowerHitPoints": 4000,
        "princessTowersHitPoints": [1200],
        "elixirLeaked": 2.0,
        "cards": [{**c, "level": opp_level} for c in (opp_cards or OPP_DECK)],
    }
    if trophy_change is not None:
        me["trophyChange"] = trophy_change
        me["startingTrophies"] = 10000
    if opp_trophy_change is not None:
        opp["trophyChange"] = opp_trophy_change
    return {
        "type": btype,
        "battleTime": t.strftime("%Y%m%dT%H%M%S.000Z"),
        "gameMode": {"id": 72000006, "name": mode},
        "arena": {"id": 54000131, "name": "Arena"},
        "deckSelection": "collection",
        "leagueNumber": 1,
        "team": [me],
        "opponent": [opp],
        **extra,
    }
