"""FastAPI dependencies for settings, authentication, and service injection."""

from secrets import compare_digest
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import Settings
from backend.app.errors import ApiException
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import VlcClientProtocol

bearer_scheme = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_vlc_client(request: Request) -> VlcClientProtocol:
    return cast(VlcClientProtocol, request.app.state.vlc_client)


def get_status_coordinator(request: Request) -> StatusCoordinator:
    return cast(StatusCoordinator, request.app.state.status_coordinator)


async def require_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    """Reject missing or invalid tokens using a constant-time comparison."""

    configured_token = settings.vlc_remote_access_token
    provided_token = credentials.credentials if credentials is not None else ""
    expected_token = (
        configured_token.get_secret_value()
        if configured_token is not None
        else "\0" * 32
    )
    valid = configured_token is not None and compare_digest(
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
