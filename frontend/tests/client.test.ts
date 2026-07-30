import { createRemoteApi, RemoteApiError } from "../src/api/client";
import { describe, expect, it, vi } from "vitest";

const TOKEN = "c".repeat(43);

const status = {
  connection: { backend: "online", vlc: "online" },
  state: "paused" as const,
  media: { title: "Example Film", filename: "example-film.mkv" },
  time: { elapsedSeconds: 15, durationSeconds: 120, position: 0.125 },
  audio: { volumePercent: 70, muted: false },
  playbackRate: 1,
  tracks: { audio: [], subtitles: [] },
  capabilities: {
    seek: true,
    volume: true,
    rate: true,
    audioTrackSelection: false,
    subtitleTrackSelection: false,
    fullscreen: false,
    playlistNavigation: false
  },
  updatedAt: "2026-07-29T12:00:00Z"
};

describe("remote API client", () => {
  it("uses fixed same-origin endpoints and a bearer token", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(status), { status: 200 })
    );
    const api = createRemoteApi(TOKEN, fetchMock);

    await api.seekRelative(-10);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/playback/seek",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin"
      })
    );
    const options = fetchMock.mock.calls[0]?.[1];
    expect(options?.headers).toBeInstanceOf(Headers);
    expect((options?.headers as Headers).get("Authorization")).toBe(
      `Bearer ${TOKEN}`
    );
    expect(options?.body).toBe('{"mode":"relative","seconds":-10}');
  });

  it("sends VLC's visible 0–200 volume scale unchanged to the API", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(status), { status: 200 })
    );
    const api = createRemoteApi(TOKEN, fetchMock);

    await api.setVolume(180);

    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe('{"percent":180}');
  });

  it("lists and plays only opaque IDs from the local movie library", async () => {
    const movieId = "d".repeat(24);
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            movies: [
              {
                id: movieId,
                title: "The Quiet Film",
                artworkQuery: "The.Quiet.Film",
                resumeSeconds: null
              }
            ]
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(status), { status: 200 }));
    const api = createRemoteApi(TOKEN, fetchMock);

    const library = await api.getLibrary();
    const movie = library.movies[0];
    expect(movie).toBeDefined();
    if (movie === undefined) {
      throw new Error("Expected a movie in the library response");
    }
    await api.playLibraryMovie(movie.id, false);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/library");
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/library/play");
    expect(fetchMock.mock.calls[1]?.[1]?.body).toBe(
      `{"movieId":"${movieId}","resume":false}`
    );
  });

  it("converts the standard server error into a safe typed error", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "VLC_UNAVAILABLE",
            message: "Remote service found, but VLC is not responding.",
            retryable: true
          }
        }),
        { status: 503 }
      )
    );
    const api = createRemoteApi(TOKEN, fetchMock);

    await expect(api.getStatus()).rejects.toEqual(
      expect.objectContaining<Partial<RemoteApiError>>({
        code: "VLC_UNAVAILABLE",
        retryable: true,
        status: 503
      })
    );
  });
});
