"""FastAPI dependencies for settings, authentication, and service injection."""

from secrets import compare_digest
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import Settings
from backend.app.errors import ApiException
from backend.app.services.movie_artwork import MovieArtworkLookupProtocol
from backend.app.services.movie_library import MovieLibraryProtocol
from backend.app.services.opensubtitles import OpenSubtitlesClientProtocol
from backend.app.services.remote_shutdown import RemoteShutdownProtocol
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import VlcClientProtocol

bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_vlc_client(request: Request) -> VlcClientProtocol:
    return cast(VlcClientProtocol, request.app.state.vlc_client)


def get_status_coordinator(request: Request) -> StatusCoordinator:
    return cast(StatusCoordinator, request.app.state.status_coordinator)


def get_artwork_lookup(request: Request) -> MovieArtworkLookupProtocol:
    return cast(MovieArtworkLookupProtocol, request.app.state.artwork_lookup)


def get_movie_library(request: Request) -> MovieLibraryProtocol:
    return cast(MovieLibraryProtocol, request.app.state.movie_library)


def get_opensubtitles_client(request: Request) -> OpenSubtitlesClientProtocol:
    return cast(OpenSubtitlesClientProtocol, request.app.state.opensubtitles_client)


def get_remote_shutdown(request: Request) -> RemoteShutdownProtocol:
    return cast(RemoteShutdownProtocol, request.app.state.remote_shutdown)


async def require_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    """Reject missing or invalid tokens using a constant-time comparison."""

    configured_token = settings.get_access_token()
    provided_token = credentials.credentials if credentials is not None else ""
    expected_token = configured_token.get_secret_value()
    valid = compare_digest(
        provided_token.encode(),
        expected_token.encode(),
    )
    if not valid:
        raise ApiException(
            status_code=401,
            code="UNAUTHORIZED",
            message="This phone is not paired with the Mac remote.",
            retryable=False,
            headers={"WWW-Authenticate": "Bearer"},
        )
