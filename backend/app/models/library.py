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


class FolderSubtitle(PlaybackModel):
    """A subtitle file safely located beside a library movie."""

    id: str = Field(pattern=r"^[a-f0-9]{24}$")
    name: str = Field(min_length=1, max_length=240)


class MovieSubtitlesResponse(PlaybackModel):
    """Locally available subtitle files for one selected library movie."""

    movie_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    subtitles: tuple[FolderSubtitle, ...]


class OnlineSubtitle(PlaybackModel):
    """One safe, short-lived result returned by OpenSubtitles for a library movie."""

    id: str = Field(pattern=r"^[a-f0-9]{24}$")
    filename: str = Field(min_length=1, max_length=240)
    language: str = Field(min_length=2, max_length=16)
    release: str | None = Field(default=None, max_length=512)
    downloads: int = Field(default=0, ge=0)
    trusted: bool = False
    hearing_impaired: bool = False
    moviehash_match: bool = False
    release_match: bool = False


class OnlineSubtitlesResponse(PlaybackModel):
    """Search results scoped to one selected local movie and language."""

    movie_id: str = Field(pattern=r"^[a-f0-9]{24}$")
    language: str = Field(min_length=2, max_length=16)
    subtitles: tuple[OnlineSubtitle, ...]


class PlayLibraryMovieRequest(CommandModel):
    """An opaque movie identifier issued by the library listing endpoint."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    movie_id: str = Field(alias="movieId", pattern=r"^[a-f0-9]{24}$")


class ActivateFolderSubtitleRequest(CommandModel):
    """Select one validated subtitle file beside a selected movie."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    subtitle_id: str = Field(alias="subtitleId", pattern=r"^[a-f0-9]{24}$")
