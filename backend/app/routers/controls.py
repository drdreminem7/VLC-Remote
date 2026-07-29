"""Authenticated, strictly typed playback and audio commands."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.dependencies import (
    get_status_coordinator,
    get_vlc_client,
    require_access_token,
)
from backend.app.models.commands import (
    AbsoluteSeekRequest,
    MuteRequest,
    RateRequest,
    RelativeSeekRequest,
    SeekRequest,
    VolumeRequest,
)
from backend.app.models.playback import VlcStatus
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import VlcClientProtocol

router = APIRouter(
    tags=["controls"],
    dependencies=[Depends(require_access_token)],
)


def remember(
    status: VlcStatus,
    coordinator: StatusCoordinator,
) -> VlcStatus:
    coordinator.remember(status)
    return status


@router.post("/playback/toggle", response_model=VlcStatus)
async def toggle_playback(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.toggle_playback(), coordinator)


@router.post("/playback/play", response_model=VlcStatus)
async def play(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.play(), coordinator)


@router.post("/playback/pause", response_model=VlcStatus)
async def pause(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.pause(), coordinator)


@router.post("/playback/stop", response_model=VlcStatus)
async def stop(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.stop(), coordinator)


@router.post("/playback/seek", response_model=VlcStatus)
async def seek(
    request: SeekRequest,
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    if isinstance(request, RelativeSeekRequest):
        result = await vlc_client.seek_relative(request.seconds)
    elif isinstance(request, AbsoluteSeekRequest):
        result = await vlc_client.seek_absolute(request.seconds)
    else:  # pragma: no cover - guarded by Pydantic's discriminated union
        raise AssertionError("Unhandled seek request")
    return remember(result, coordinator)


@router.post("/playback/rate", response_model=VlcStatus)
async def set_rate(
    request: RateRequest,
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.set_rate(request.rate), coordinator)


@router.post("/audio/volume", response_model=VlcStatus)
async def set_volume(
    request: VolumeRequest,
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.set_volume(request.percent), coordinator)


@router.post("/audio/mute", response_model=VlcStatus)
async def set_muted(
    request: MuteRequest,
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    return remember(await vlc_client.set_muted(request.muted), coordinator)
