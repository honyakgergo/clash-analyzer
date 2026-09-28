import httpx
import pytest

from clash_analyzer.clash.client import (
    AccessDeniedError,
    ClashAPIError,
    NotFoundError,
    RateLimitedError,
)

from .conftest import PLAYER_TAG, FakeAPI


async def test_player_request_encodes_tag_and_sends_auth(make_client) -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"tag": PLAYER_TAG})

    client = make_client(FakeAPI({f"/v1/players/{PLAYER_TAG}": handler}))
    assert (await client.player("pqggvojp"))["tag"] == PLAYER_TAG
    assert seen[0].url.raw_path == b"/v1/players/%23PQGGV0JP"
    assert seen[0].headers["authorization"] == "Bearer test-key"


async def test_cache_honours_max_age(make_client) -> None:
    api = FakeAPI()
    client = make_client(api)
    await client.player(PLAYER_TAG)
    await client.player(PLAYER_TAG)
    assert api.calls.count(f"/v1/players/{PLAYER_TAG}") == 1


async def test_no_cache_without_max_age(make_client) -> None:
    api = FakeAPI({"/v1/x": lambda r: httpx.Response(200, json={})})
    client = make_client(api)
    await client.get("/x")
    await client.get("/x")
    assert len(api.calls) == 2


async def test_retries_on_429_then_succeeds(make_client, monkeypatch) -> None:
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    responses = iter(
        [httpx.Response(429, headers={"retry-after": "0"}), httpx.Response(200, json={"ok": 1})]
    )
    client = make_client(FakeAPI({"/v1/x": lambda r: next(responses)}))
    assert await client.get("/x") == {"ok": 1}


async def test_gives_up_after_max_retries(make_client, monkeypatch) -> None:
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    api = FakeAPI({"/v1/x": lambda r: httpx.Response(503, json={"reason": "inMaintenance"})})
    client = make_client(api, max_retries=2)
    with pytest.raises(ClashAPIError) as exc:
        await client.get("/x")
    assert exc.value.status == 503
    assert len(api.calls) == 3


@pytest.mark.parametrize(
    ("status", "error"),
    [(404, NotFoundError), (403, AccessDeniedError), (400, ClashAPIError)],
)
async def test_error_mapping(make_client, status: int, error: type) -> None:
    client = make_client(
        FakeAPI({"/v1/x": lambda r: httpx.Response(status, json={"reason": "r", "message": "m"})})
    )
    with pytest.raises(error) as exc:
        await client.get("/x")
    assert exc.value.reason == "r"


async def test_429_without_retries_is_rate_limited(make_client) -> None:
    client = make_client(FakeAPI({"/v1/x": lambda r: httpx.Response(429)}), max_retries=0)
    with pytest.raises(RateLimitedError):
        await client.get("/x")


async def test_endpoint_helpers_unwrap_items(client) -> None:
    assert len(await client.upcoming_chests(PLAYER_TAG)) > 0
    assert len(await client.path_of_legend_ranking(limit=3)) == 3
    assert len((await client.cards())["items"]) > 100


async def _no_sleep(_seconds: float) -> None:
    return None
