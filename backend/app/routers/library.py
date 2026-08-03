"""Authenticated movie-library listing and fixed play operation."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.dependencies import (
    get_movie_library,
    get_opensubtitles_client,
    get_status_coordinator,
    get_vlc_client,
    require_access_token,
)
from backend.app.errors import ApiException
from backend.app.models.library import (
    ActivateFolderSubtitleRequest,
    MovieLibraryResponse,
    MovieSubtitlesResponse,
    OnlineSubtitlesResponse,
    PlayLibraryMovieRequest,
)
from backend.app.models.playback import VlcStatus
from backend.app.routers.controls import remember
from backend.app.services.movie_library import MovieLibraryProtocol
from backend.app.services.opensubtitles import OpenSubtitlesClientProtocol
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
    result = await vlc_client.play_media(file_path, subtitle_paths)
    return remember(result, coordinator)


@router.get("/{movie_id}/subtitles", response_model=MovieSubtitlesResponse)
async def list_folder_subtitles(
    movie_id: str,
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
) -> MovieSubtitlesResponse:
    subtitles = await movie_library.folder_subtitles(movie_id)
    if not subtitles:
        file_path = await movie_library.resolve_movie(movie_id)
        if file_path is None:
            raise ApiException(
                status_code=404,
                code="INVALID_REQUEST",
                message="That movie is no longer available in the local library.",
                retryable=False,
            )
    return MovieSubtitlesResponse(movie_id=movie_id, subtitles=subtitles)


@router.post("/{movie_id}/subtitles/activate", response_model=VlcStatus)
async def activate_folder_subtitle(
    movie_id: str,
    request: ActivateFolderSubtitleRequest,
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    subtitle_path = await movie_library.resolve_folder_subtitle(
        movie_id, request.subtitle_id
    )
    if subtitle_path is None:
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="That subtitle is no longer available beside this movie.",
            retryable=False,
        )
    movie_path = await movie_library.resolve_movie(movie_id)
    if movie_path is None:
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="That movie is no longer available in the local library.",
            retryable=False,
        )
    return remember(
        await vlc_client.add_subtitle(subtitle_path, movie_path), coordinator
    )


@router.get("/{movie_id}/subtitles/online", response_model=OnlineSubtitlesResponse)
async def search_online_subtitles(
    movie_id: str,
    language: Annotated[str, Query(pattern=r"^[a-z]{2,3}(?:-[a-z]{2})?$")],
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
    opensubtitles_client: Annotated[
        OpenSubtitlesClientProtocol, Depends(get_opensubtitles_client)
    ],
) -> OnlineSubtitlesResponse:
    movie_path = await movie_library.resolve_movie(movie_id)
    if movie_path is None:
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="That movie is no longer available in the local library.",
            retryable=False,
        )
    return OnlineSubtitlesResponse(
        movie_id=movie_id,
        language=language,
        subtitles=await opensubtitles_client.search(movie_path, language),
    )


@router.post(
    "/{movie_id}/subtitles/online/{subtitle_id}/download", response_model=VlcStatus
)
async def download_online_subtitle(
    movie_id: str,
    subtitle_id: str,
    movie_library: Annotated[MovieLibraryProtocol, Depends(get_movie_library)],
    opensubtitles_client: Annotated[
        OpenSubtitlesClientProtocol, Depends(get_opensubtitles_client)
    ],
    vlc_client: Annotated[VlcClientProtocol, Depends(get_vlc_client)],
    coordinator: Annotated[StatusCoordinator, Depends(get_status_coordinator)],
) -> VlcStatus:
    movie_path = await movie_library.resolve_movie(movie_id)
    if movie_path is None:
        raise ApiException(
            status_code=404,
            code="INVALID_REQUEST",
            message="That movie is no longer available in the local library.",
            retryable=False,
        )
    subtitle_path = await opensubtitles_client.download(movie_path, subtitle_id)
    return remember(
        await vlc_client.add_subtitle(subtitle_path, movie_path), coordinator
    )
