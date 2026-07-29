"""FastAPI application factory and same-origin frontend serving."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.app import __version__
from backend.app.config import Settings, get_settings
from backend.app.errors import (
    ApiException,
    VlcError,
    api_exception_handler,
    validation_exception_handler,
    vlc_exception_handler,
)
from backend.app.routers.controls import router as controls_router
from backend.app.routers.health import router as health_router
from backend.app.routers.status import router as status_router
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import (
    HttpxVlcClient,
    UnconfiguredVlcClient,
    VlcClientProtocol,
)


def frontend_directory() -> Path:
    """Return the Vite production-output directory."""

    return Path(__file__).resolve().parent / "static"


def create_app(
    *,
    settings: Settings | None = None,
    vlc_client: VlcClientProtocol | None = None,
) -> FastAPI:
    """Build an application instance suitable for production and tests."""

    active_settings = settings or get_settings()
    if vlc_client is not None:
        active_vlc_client = vlc_client
    elif active_settings.vlc_is_configured:
        active_vlc_client = HttpxVlcClient.from_settings(active_settings)
    else:
        active_vlc_client = UnconfiguredVlcClient()

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        yield
        if isinstance(active_vlc_client, HttpxVlcClient):
            await active_vlc_client.aclose()

    application = FastAPI(
        title="Mac VLC Remote",
        version=__version__,
        description="Local, mobile-first control service for VLC on macOS.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.vlc_client = active_vlc_client
    application.state.status_coordinator = StatusCoordinator()

    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=active_settings.allowed_hosts,
    )
    application.add_exception_handler(ApiException, api_exception_handler)
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    application.add_exception_handler(VlcError, vlc_exception_handler)

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(status_router, prefix="/api/v1")
    application.include_router(controls_router, prefix="/api/v1")

    @application.api_route(
        "/api/{unmatched_path:path}",
        methods=["DELETE", "GET", "PATCH", "POST", "PUT"],
        include_in_schema=False,
    )
    async def unknown_api_route(unmatched_path: str) -> None:
        del unmatched_path
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="The requested API endpoint does not exist.",
            retryable=False,
        )

    static_directory = frontend_directory()
    if (static_directory / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=static_directory, html=True),
            name="frontend",
        )
    else:

        @application.get("/", include_in_schema=False)
        async def frontend_not_built() -> HTMLResponse:
            return HTMLResponse(
                """
                <!doctype html>
                <html lang="en">
                  <head><meta charset="utf-8"><title>Mac VLC Remote</title></head>
                  <body>
                    <main>
                      <h1>Frontend not built</h1>
                      <p>
                        Run <code>npm run build</code> or use
                        <code>make dev</code>.
                      </p>
                    </main>
                  </body>
                </html>
                """.strip()
            )

    return application


app = create_app()
