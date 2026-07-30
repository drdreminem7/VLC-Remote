"""Authenticated normalized playback status."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.dependencies import (
    get_playback_resume_tracker,
    get_status_coordinator,
    get_vlc_client,
    require_access_token,
)
from backend.app.models.playback import VlcStatus
from backend.app.services.playback_resume import PlaybackResumeTracker
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import VlcClientProtocol

router = APIRouter(
    tags=["status"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/status", response_model=VlcStatus)
async def status(
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
    tracker: Annotated[PlaybackResumeTracker, Depends(get_playback_resume_tracker)],
) -> VlcStatus:
    """Return a briefly cached, normalized VLC status."""

    result = await coordinator.get_status(vlc_client)
    await tracker.observe(result)
    return result
