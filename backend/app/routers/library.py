"""Authenticated movie-library listing and fixed play operation."""

from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.dependencies import (
    get_movie_library,
    get_status_coordinator,
    get_vlc_client,
    require_access_token,
)
from backend.app.errors import ApiException
from backend.app.models.library import (
    MovieLibraryResponse,
    PlayLibraryMovieRequest,
)
from backend.app.models.playback import VlcStatus
from backend.app.routers.controls import remember
from backend.app.services.movie_library import MovieLibraryProtocol
from backend.app.services.status_coordinator import StatusCoordinator
from backend.app.services.vlc_client import VlcClientProtocol

router = APIRouter(
    prefix="/library",
    tags=["library"],
    dependencies=[Depends(require_access_token)],
)


@router.get("", response_model=MovieLibraryResponse)
async def list_movies(
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
) -> MovieLibraryResponse:
    return MovieLibraryResponse(movies=await movie_library.list_movies())


@router.post("/play", response_model=VlcStatus)
async def play_movie(
    request: PlayLibraryMovieRequest,
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    file_path = await movie_library.resolve_movie(request.movie_id)
    if file_path is None:
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="That movie is no longer available in the local library.",
            retryable=False,
        )
    subtitle_paths = await movie_library.subtitles_for(file_path)
    return remember(await vlc_client.play_media(file_path, subtitle_paths), coordinator)
