"""Async client for the official Clash Royale API.

Features: bearer auth, a TTL cache that honours ``cache-control: max-age``, request
spacing (the API rate limits per IP and sometimes answers 403 instead of 429), and
retry with backoff on 429/5xx.
"""

import asyncio
import re
import time
from typing import Any

import httpx

from .tags import encode_tag

_MAX_AGE_RE = re.compile(r"max-age=(\d+)")


class ClashAPIError(Exception):
    def __init__(self, status: int, reason: str, message: str = "") -> None:
        self.status = status
        self.reason = reason
        self.message = message
        super().__init__(f"Clash API {status} {reason}: {message}".rstrip(": "))


class NotFoundError(ClashAPIError):
    pass


class AccessDeniedError(ClashAPIError):
    pass


class RateLimitedError(ClashAPIError):
    pass


class ClashClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.clashroyale.com/v1",
        *,
        timeout_s: float = 15.0,
        min_interval_s: float = 0.12,
        max_retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=timeout_s,
            transport=transport,
        )
        self._min_interval = min_interval_s
        self._max_retries = max_retries
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self.requests_made = 0

    async def aclose(self) -> None:
        await self._http.aclose()

    # -- low level ---------------------------------------------------------------------------

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._last_request + self._min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    async def get(
        self, path: str, params: dict[str, Any] | None = None, *, min_ttl_s: float = 0
    ) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        key = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        cached = self._cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        for attempt in range(self._max_retries + 1):
            await self._throttle()
            self.requests_made += 1
            try:
                resp = await self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise ClashAPIError(0, "networkError", str(exc)) from exc
                await asyncio.sleep(0.5 * 2**attempt)
                continue

            if resp.status_code == 200:
                data = resp.json()
                ttl = max(_max_age(resp), min_ttl_s)
                if ttl > 0:
                    self._cache[key] = (time.monotonic() + ttl, data)
                return data

            retryable = resp.status_code == 429 or resp.status_code >= 500
            if retryable and attempt < self._max_retries:
                retry_after = resp.headers.get("retry-after")
                delay = float(retry_after) if retry_after else 0.5 * 2**attempt
                await asyncio.sleep(min(delay, 10))
                continue
            raise _error_from(resp)
        raise AssertionError("unreachable")  # pragma: no cover

    # -- endpoints ---------------------------------------------------------------------------

    async def player(self, tag: str) -> dict[str, Any]:
        return await self.get(f"/players/{encode_tag(tag)}")

    async def battlelog(self, tag: str) -> list[dict[str, Any]]:
        return await self.get(f"/players/{encode_tag(tag)}/battlelog")

    async def upcoming_chests(self, tag: str) -> list[dict[str, Any]]:
        data = await self.get(f"/players/{encode_tag(tag)}/upcomingchests")
        return data.get("items", [])

    async def cards(self) -> dict[str, Any]:
        # The catalog barely changes; keep it for an hour regardless of max-age.
        return await self.get("/cards", min_ttl_s=3600)

    async def clan(self, tag: str) -> dict[str, Any]:
        return await self.get(f"/clans/{encode_tag(tag)}")

    async def current_river_race(self, tag: str) -> dict[str, Any]:
        return await self.get(f"/clans/{encode_tag(tag)}/currentriverrace")

    async def river_race_log(self, tag: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self.get(f"/clans/{encode_tag(tag)}/riverracelog", {"limit": limit})
        return data.get("items", [])

    async def path_of_legend_ranking(
        self, location: str = "global", limit: int = 100
    ) -> list[dict[str, Any]]:
        data = await self.get(f"/locations/{location}/pathoflegend/players", {"limit": limit})
        return data.get("items", [])

    async def path_of_legend_season_ranking(
        self, season_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        data = await self.get(
            f"/locations/global/pathoflegend/{season_id}/rankings/players", {"limit": limit}
        )
        return data.get("items", [])

    async def seasons(self) -> list[str]:
        data = await self.get("/locations/global/seasons", min_ttl_s=3600)
        return [s["id"] for s in data.get("items", [])]


def _max_age(resp: httpx.Response) -> int:
    match = _MAX_AGE_RE.search(resp.headers.get("cache-control", ""))
    return int(match.group(1)) if match else 0


def _error_from(resp: httpx.Response) -> ClashAPIError:
    try:
        body = resp.json()
    except ValueError:
        body = {}
    reason = body.get("reason", "unknown") if isinstance(body, dict) else "unknown"
    message = (body.get("message") or "") if isinstance(body, dict) else ""
    cls: type[ClashAPIError] = ClashAPIError
    if resp.status_code == 404:
        cls = NotFoundError
    elif resp.status_code == 403:
        cls = AccessDeniedError
    elif resp.status_code == 429:
        cls = RateLimitedError
    return cls(resp.status_code, reason, message)
