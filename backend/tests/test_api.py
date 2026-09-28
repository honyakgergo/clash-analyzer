import time

import httpx
from fastapi.testclient import TestClient

from clash_analyzer.main import create_app

from .conftest import CLAN_TAG, PLAYER_TAG, FakeAPI


def test_health(api: TestClient) -> None:
    body = api.get("/api/health").json()
    assert body["status"] == "ok" and body["api_key_configured"] is True


def test_health_does_not_leak_key(api: TestClient) -> None:
    assert "test-key" not in api.get("/api/health").text


def test_get_player_normalizes_tag_and_ingests(api: TestClient) -> None:
    r = api.get("/api/players/pqggvojp")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["tag"] == PLAYER_TAG
    assert body["battles_stored"] == 30 and body["snapshots_stored"] == 1
    assert body["tracked"] is False


def test_invalid_tag_is_422(api: TestClient) -> None:
    r = api.get("/api/players/HELLO")
    assert r.status_code == 422 and r.json()["error"] == "invalid_tag"


def test_unknown_player_is_404(api: TestClient) -> None:
    r = api.get("/api/players/%23CCCCCC")
    assert r.status_code == 404 and r.json()["error"] == "not_found"


def test_access_denied_maps_to_502(settings, make_client) -> None:
    api_ = FakeAPI(
        {
            f"/v1/players/{PLAYER_TAG}": lambda r: httpx.Response(
                403, json={"reason": "accessDenied"}
            )
        }
    )
    with TestClient(create_app(settings, client=make_client(api_))) as tc:
        r = tc.get(f"/api/players/{PLAYER_TAG[1:]}")
    assert r.status_code == 502 and r.json()["error"] == "access_denied"


def test_track_untrack_and_list(api: TestClient) -> None:
    assert api.post("/api/players/PQGGV0JP/track").json()["tracked"] is True
    tracked = api.get("/api/players/tracked").json()
    assert [p["tag"] for p in tracked] == [PLAYER_TAG]
    assert api.delete("/api/players/PQGGV0JP/track").json()["tracked"] is False
    assert api.get("/api/players/tracked").json() == []


def test_player_subresources(api: TestClient) -> None:
    for path in (
        "progress",
        "collection",
        "mastery",
        "upgrades",
        "analytics",
        "chests",
        "battles",
        "meta-compare",
    ):
        r = api.get(f"/api/players/PQGGV0JP/{path}")
        assert r.status_code == 200, (path, r.text)


def test_battles_pagination_and_mode(api: TestClient) -> None:
    page = api.get("/api/players/PQGGV0JP/battles?limit=5&offset=5").json()
    assert len(page["items"]) == 5
    assert page["items"][0]["battle_time"].endswith("Z")
    assert api.get("/api/players/PQGGV0JP/battles?mode=war").json()["items"] == []


def test_analytics_params_validated(api: TestClient) -> None:
    assert api.get("/api/players/PQGGV0JP/analytics?days=0").status_code == 422
    assert api.get("/api/players/PQGGV0JP/upgrades?target_level=17").status_code == 422
    assert api.get("/api/players/PQGGV0JP/upgrades?target_level=14").json()["target_level"] == 14


def test_force_refresh(api: TestClient) -> None:
    api.get("/api/players/PQGGV0JP")
    assert api.post("/api/players/PQGGV0JP/refresh").json()["new_battles"] == 0


def test_clan_endpoint(api: TestClient) -> None:
    r = api.get(f"/api/clans/{CLAN_TAG[1:]}")
    assert r.status_code == 200 and r.json()["members"]


def test_meta_crawl_via_api(api: TestClient) -> None:
    assert api.get("/api/meta/status").json() == {"running": False, "last_crawl": None}
    assert api.post("/api/meta/refresh").json()["started"] is True
    for _ in range(100):
        status = api.get("/api/meta/status").json()
        if not status["running"]:
            break
        time.sleep(0.05)
    assert status["last_crawl"]["status"] == "done"
    assert status["last_crawl"]["started_at"].endswith("Z")
    body = api.get("/api/meta?mode=all&min_deck_games=1").json()
    assert body["decks_observed"] > 0 and body["cards"]
