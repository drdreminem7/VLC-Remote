"""Authenticated movie artwork lookup."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.dependencies import get_artwork_lookup, require_access_token
from backend.app.models.artwork import ArtworkResponse
from backend.app.services.movie_artwork import MovieArtworkLookupProtocol

router = APIRouter(
    tags=["artwork"],
    dependencies=[Depends(require_access_token)],
)


@router.get("/artwork", response_model=ArtworkResponse)
async def artwork(
    title: Annotated[str, Query(min_length=1, max_length=256)],
    lookup: Annotated[MovieArtworkLookupProtocol, Depends(get_artwork_lookup)],
) -> ArtworkResponse:
    return ArtworkResponse(image_data=await lookup.lookup(title))
