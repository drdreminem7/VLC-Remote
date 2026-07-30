from pathlib import Path

from backend.app.services.movie_library import MovieLibrary


async def test_library_lists_supported_movies_without_exposing_paths(
    tmp_path: Path,
) -> None:
    movie_path = tmp_path / "Drama" / "The.Quiet.Film.2024.1080p.BluRay.mkv"
    movie_path.parent.mkdir()
    movie_path.touch()
    (tmp_path / "Notes.txt").touch()
    (tmp_path / ".hidden.mp4").touch()

    library = MovieLibrary(tmp_path)

    movies = await library.list_movies()

    assert len(movies) == 1
    assert movies[0].title == "The Quiet Film 2024"
    assert movies[0].artwork_query == "The.Quiet.Film.2024.1080p.BluRay"
    assert str(tmp_path) not in movies[0].model_dump_json()


async def test_library_resolves_only_ids_from_its_current_listing(
    tmp_path: Path,
) -> None:
    movie_path = tmp_path / "Film.mkv"
    movie_path.touch()
    library = MovieLibrary(tmp_path)

    movie = (await library.list_movies())[0]

    assert await library.resolve_movie(movie.id) == movie_path.resolve()
    assert await library.resolve_movie("0" * 24) is None


async def test_library_returns_only_valid_subtitles_beside_the_selected_movie(
    tmp_path: Path,
) -> None:
    movie_path = tmp_path / "Film" / "Film.mkv"
    movie_path.parent.mkdir()
    movie_path.touch()
    english_subtitle = movie_path.with_suffix(".en.srt")
    english_subtitle.touch()
    commentary_subtitle = movie_path.with_suffix(".commentary.ass")
    commentary_subtitle.touch()
    (movie_path.parent / "Notes.txt").touch()
    (movie_path.parent / ".hidden.srt").touch()
    (tmp_path / "Other" / "Elsewhere.srt").parent.mkdir()
    (tmp_path / "Other" / "Elsewhere.srt").touch()
    library = MovieLibrary(tmp_path)

    subtitles = await library.subtitles_for(movie_path.resolve())

    assert subtitles == (commentary_subtitle.resolve(), english_subtitle.resolve())


async def test_missing_library_is_an_empty_library(tmp_path: Path) -> None:
    library = MovieLibrary(tmp_path / "does-not-exist")

    assert await library.list_movies() == ()
