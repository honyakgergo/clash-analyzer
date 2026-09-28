"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .clash.client import (
    AccessDeniedError,
    ClashAPIError,
    ClashClient,
    NotFoundError,
    RateLimitedError,
)
from .clash.tags import InvalidTagError
from .config import Settings, get_settings
from .db import init_db, make_engine
from .deps import AppState
from .routers import general, players
from .scheduler import build_scheduler

log = logging.getLogger("clash_analyzer")


def create_app(settings: Settings | None = None, client: ClashClient | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        init_db(engine)
        api = client or ClashClient(
            settings.cr_api_key.get_secret_value(),
            settings.cr_api_base,
            timeout_s=settings.request_timeout_s,
            min_interval_s=settings.min_request_interval_s,
            max_retries=settings.max_retries,
        )
        state = AppState(settings=settings, engine=engine, client=api)
        app.state.app_state = state
        scheduler = build_scheduler(state) if settings.scheduler_enabled else None
        if scheduler:
            scheduler.start()
        if not settings.cr_api_key.get_secret_value():
            log.warning("CR_API_KEY is not set; API calls will fail. See backend/.env.example")
        try:
            yield
        finally:
            if scheduler:
                scheduler.shutdown(wait=False)
            if state.meta_task and not state.meta_task.done():
                state.meta_task.cancel()
            await api.aclose()
            engine.dispose()

    app = FastAPI(title="Clash Analyzer", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(general.router)
    app.include_router(players.router)
    _register_errors(app)
    return app


def _register_errors(app: FastAPI) -> None:
    def err(status: int, code: str, detail: str) -> JSONResponse:
        return JSONResponse(status_code=status, content={"error": code, "detail": detail})

    @app.exception_handler(InvalidTagError)
    async def _invalid_tag(_: Request, exc: InvalidTagError) -> JSONResponse:
        return err(422, "invalid_tag", str(exc))

    @app.exception_handler(ClashAPIError)
    async def _clash(_: Request, exc: ClashAPIError) -> JSONResponse:
        if isinstance(exc, NotFoundError):
            return err(404, "not_found", "Not found in Clash Royale. Check the tag.")
        if isinstance(exc, AccessDeniedError):
            return err(
                502,
                "access_denied",
                "The Clash Royale API rejected the key. It's probably missing, or your IP is "
                "not whitelisted (or you're rate limited).",
            )
        if isinstance(exc, RateLimitedError):
            return err(
                503, "rate_limited", "Rate limited by the Clash Royale API. Try again shortly."
            )
        if exc.status == 503:
            return err(503, "maintenance", "The Clash Royale API is in maintenance.")
        return err(502, "upstream_error", str(exc))


app = create_app()
