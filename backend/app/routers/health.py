"""Public, secret-free service health route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app import __version__
from backend.app.dependencies import get_vlc_client
from backend.app.models.api import (
    BackendHealth,
    HealthResponse,
    VlcHealth,
    VlcHealthStatus,
)
from backend.app.services.vlc_client import VlcClientProtocol

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
) -> HealthResponse:
    """Report backend availability without exposing settings or exceptions."""

    availability = await vlc_client.probe()
    if not availability.checked:
        vlc_status: VlcHealthStatus = "not_configured"
    elif availability.reachable:
        vlc_status = "online"
    else:
        vlc_status = "unavailable"

    return HealthResponse(
        backend=BackendHealth(version=__version__),
        vlc=VlcHealth(
            status=vlc_status,
            reachable=availability.reachable,
            checked=availability.checked,
        ),
    )
