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
    OpenSubtitlesError,
    VlcError,
    api_exception_handler,
    opensubtitles_exception_handler,
    validation_exception_handler,
    vlc_exception_handler,
)
from backend.app.routers.artwork import router as artwork_router
from backend.app.routers.controls import router as controls_router
from backend.app.routers.health import router as health_router
from backend.app.routers.library import router as library_router
from backend.app.routers.status import router as status_router
from backend.app.services.movie_artwork import (
    MovieArtworkLookup,
    MovieArtworkLookupProtocol,
)
from backend.app.services.movie_library import MovieLibrary, MovieLibraryProtocol
from backend.app.services.opensubtitles import (
    OpenSubtitlesClient,
    OpenSubtitlesClientProtocol,
    UnconfiguredOpenSubtitlesClient,
)
from backend.app.services.remote_shutdown import (
    ProcessRemoteShutdown,
    RemoteShutdownProtocol,
)
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
    artwork_lookup: MovieArtworkLookupProtocol | None = None,
    movie_library: MovieLibraryProtocol | None = None,
    opensubtitles_client: OpenSubtitlesClientProtocol | None = None,
    remote_shutdown: RemoteShutdownProtocol | None = None,
) -> FastAPI:
    """Build an application instance suitable for production and tests."""

    active_settings = settings or get_settings()
    if vlc_client is not None:
        active_vlc_client = vlc_client
    elif active_settings.vlc_is_configured:
        active_vlc_client = HttpxVlcClient.from_settings(active_settings)
    else:
        active_vlc_client = UnconfiguredVlcClient()
    active_artwork_lookup = artwork_lookup or MovieArtworkLookup(
        tmdb_api_token=(
            active_settings.tmdb_api_token.get_secret_value()
            if active_settings.tmdb_api_token is not None
            else None
        )
    )
    active_movie_library = movie_library or MovieLibrary(
        active_settings.movie_library_directory
    )
    if opensubtitles_client is not None:
        active_opensubtitles_client = opensubtitles_client
    elif active_settings.opensubtitles_is_configured:
        active_opensubtitles_client = OpenSubtitlesClient.from_settings(active_settings)
    else:
        active_opensubtitles_client = UnconfiguredOpenSubtitlesClient()
    active_remote_shutdown = remote_shutdown or ProcessRemoteShutdown()

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        yield
        if isinstance(active_vlc_client, HttpxVlcClient):
            await active_vlc_client.aclose()
        await active_artwork_lookup.aclose()
        await active_opensubtitles_client.aclose()

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
    application.state.artwork_lookup = active_artwork_lookup
    application.state.movie_library = active_movie_library
    application.state.opensubtitles_client = active_opensubtitles_client
    application.state.remote_shutdown = active_remote_shutdown

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
    application.add_exception_handler(
        OpenSubtitlesError, opensubtitles_exception_handler
    )

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(status_router, prefix="/api/v1")
    application.include_router(controls_router, prefix="/api/v1")
    application.include_router(artwork_router, prefix="/api/v1")
    application.include_router(library_router, prefix="/api/v1")

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
