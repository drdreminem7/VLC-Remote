"""Safe, phone-facing representations of movies in the local library."""

from pydantic import ConfigDict, Field

from backend.app.models.commands import CommandModel
from backend.app.models.playback import PlaybackModel


class LibraryMovie(PlaybackModel):
    """A movie that has already been validated as inside the configured library."""

    id: str = Field(pattern=r"^[a-f0-9]{24}$")
    title: str = Field(min_length=1, max_length=240)
    artwork_query: str = Field(min_length=1, max_length=512)


class MovieLibraryResponse(PlaybackModel):
    """The bounded set of movies the paired phone may ask VLC to play."""

    movies: tuple[LibraryMovie, ...]


class PlayLibraryMovieRequest(CommandModel):
    """An opaque movie identifier issued by the library listing endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    movie_id: str = Field(alias="movieId", pattern=r"^[a-f0-9]{24}$")
