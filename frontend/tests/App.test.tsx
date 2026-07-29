import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

const TOKEN = "t".repeat(43);

const pausedStatus = {
  connection: { backend: "online", vlc: "online" },
  state: "paused",
  media: { title: "Moonrise, Chapter Four.mkv", filename: "moonrise.mkv" },
  time: { elapsedSeconds: 1482, durationSeconds: 6420, position: 0.23 },
  audio: { volumePercent: 68, muted: false },
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

function response(payload: object, status = 200): Response {
  return new Response(JSON.stringify(payload), { status });
}

function requestUrl(input: Parameters<typeof fetch>[0]): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

function remoteFetch(
  ...responses: Array<Response | Promise<Response>>
): ReturnType<typeof vi.fn<typeof fetch>> {
  const queue = [...responses];
  return vi.fn<typeof fetch>().mockImplementation((input) => {
    if (requestUrl(input).startsWith("/api/v1/artwork")) {
      return Promise.resolve(response({ imageData: null }));
    }
    return Promise.resolve(queue.shift() ?? response(pausedStatus));
  });
}

function pairedFetch(): ReturnType<typeof vi.fn<typeof fetch>> {
  return remoteFetch(response(pausedStatus));
}

function remoteFetchWithPoster(): ReturnType<typeof vi.fn<typeof fetch>> {
  const fetchMock = remoteFetch(response(pausedStatus));
  fetchMock.mockImplementation((input) => {
    if (requestUrl(input).startsWith("/api/v1/artwork")) {
      return Promise.resolve(
        response({
          imageData: "data:image/jpeg;base64,poster"
        })
      );
    }
    return Promise.resolve(response(pausedStatus));
  });
  return fetchMock;
}

function apiUrls(fetchMock: ReturnType<typeof vi.fn<typeof fetch>>): string[] {
  return fetchMock.mock.calls
    .map(([url]) => requestUrl(url))
    .filter((url) => url.startsWith("/api/") && !url.startsWith("/api/v1/artwork"));
}

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState(null, document.title, "/");
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    value: true
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("mobile remote", () => {
  it("shows a clear pairing state without requesting protected status", () => {
    const fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Pair this phone." })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Open the pairing link from your Mac to connect this phone.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Play playback" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("extracts a pairing fragment, clears it, and renders live VLC data", async () => {
    window.history.replaceState(null, document.title, `/#token=${TOKEN}`);
    const fetchMock = pairedFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(window.location.hash).toBe("");
    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Current playback" })).toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent("Connected");
    expect(screen.getAllByText("Paused")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Play playback" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Skip backward 10 seconds" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Skip forward 10 seconds" })).toBeEnabled();
    expect(screen.getByRole("group", { name: "Volume 68 of 200" })).toBeInTheDocument();
    expect(screen.queryByText("Moonrise, Chapter Four")).not.toBeInTheDocument();
    expect(screen.queryByText("Local API protected")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/status",
      expect.objectContaining({ credentials: "same-origin" })
    );
  });

  it("shows movie artwork when a matching poster is found", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = remoteFetchWithPoster();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => {
      expect(document.querySelector(".touch-surface__artwork img")).toHaveAttribute(
        "src",
        "data:image/jpeg;base64,poster"
      );
    });
  });

  it("sends one fixed toggle request and applies the returned status", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const playingStatus = { ...pausedStatus, state: "playing" };
    const fetchMock = remoteFetch(response(pausedStatus), response(playingStatus));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const playButton = await screen.findByRole("button", { name: "Play playback" });

    fireEvent.click(playButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Pause playback" })).toBeEnabled();
    });
    expect(apiUrls(fetchMock)).toEqual([
      "/api/v1/status",
      "/api/v1/playback/toggle"
    ]);
  });

  it("keeps controls active while a command is being confirmed", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    let resolveCommand: ((value: Response) => void) | undefined;
    const commandResponse = new Promise<Response>((resolve) => {
      resolveCommand = resolve;
    });
    const playingStatus = { ...pausedStatus, state: "playing" };
    const fetchMock = remoteFetch(response(pausedStatus), commandResponse);
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const playButton = await screen.findByRole("button", { name: "Play playback" });
    fireEvent.click(playButton);

    await waitFor(() => expect(playButton).toHaveAttribute("aria-busy", "true"));
    expect(screen.getByRole("button", { name: "Skip backward 10 seconds" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Skip forward 10 seconds" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Mute audio" })).toBeEnabled();

    resolveCommand?.(response(playingStatus));
    await waitFor(() => expect(playButton).toHaveAttribute("aria-busy", "false"));
  });

  it("keeps the command response instead of briefly restoring stale mute state", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const mutedStatus = {
      ...pausedStatus,
      audio: { volumePercent: 0, muted: true }
    };
    const fetchMock = remoteFetch(response(pausedStatus), response(mutedStatus));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Mute audio" }));

    expect(await screen.findByRole("button", { name: "Unmute audio" })).toBeEnabled();
    expect(apiUrls(fetchMock)).toEqual([
      "/api/v1/status",
      "/api/v1/audio/mute"
    ]);
  });

  it("changes volume in five-unit steps", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const louderStatus = {
      ...pausedStatus,
      audio: { volumePercent: 73, muted: false }
    };
    const fetchMock = remoteFetch(response(pausedStatus), response(louderStatus));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Increase volume by 5" }));

    await waitFor(() => {
      expect(screen.getByRole("group", { name: "Volume 73 of 200" })).toBeInTheDocument();
    });
    const volumeRequest = fetchMock.mock.calls.find(
      ([url]) => url === "/api/v1/audio/volume"
    );
    expect(volumeRequest?.[1]?.body).toBe('{"percent":73}');
  });

  it("rounds VLC's imprecise playback-rate response for the speed selector", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    vi.stubGlobal("fetch", remoteFetch(response({ ...pausedStatus, playbackRate: 0.75018 })));

    render(<App />);

    expect(await screen.findByRole("combobox", { name: "Playback speed" })).toHaveValue("0.75");
    expect(screen.getByRole("option", { name: "0.75×" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "0.75018×" })).not.toBeInTheDocument();
  });

  it("previews timeline movement and only seeks when the control is released", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = pairedFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const timeline = await screen.findByLabelText(/Seek to 24:42/);

    fireEvent.change(timeline, { target: { value: "1800" } });
    expect(screen.getByText("30:00")).toBeInTheDocument();
    expect(apiUrls(fetchMock)).toEqual(["/api/v1/status"]);

    fireEvent.pointerUp(timeline);
    await waitFor(() => {
      expect(fetchMock.mock.calls.map(([url]) => url)).toContain(
        "/api/v1/playback/seek"
      );
    });
    const seekRequest = fetchMock.mock.calls.find(
      ([url]) => url === "/api/v1/playback/seek"
    );
    expect(seekRequest?.[1]?.body).toBe('{"mode":"absolute","seconds":1800}');
  });

  it("keeps a released timeline position visible until VLC confirms the seek", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    let resolveSeek: ((value: Response) => void) | undefined;
    const seekResponse = new Promise<Response>((resolve) => {
      resolveSeek = resolve;
    });
    const confirmedStatus = {
      ...pausedStatus,
      time: { ...pausedStatus.time, elapsedSeconds: 1800, position: 0.28 }
    };
    const fetchMock = remoteFetch(response(pausedStatus), seekResponse);
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const timeline = await screen.findByLabelText(/Seek to 24:42/);
    fireEvent.change(timeline, { target: { value: "1800" } });
    fireEvent.pointerUp(timeline);

    expect(screen.getByText("30:00")).toBeInTheDocument();

    resolveSeek?.(response(confirmedStatus));
    await waitFor(() => expect(screen.getByText("30:00")).toBeInTheDocument());
  });

  it("seeks when a timeline position is tapped", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = pairedFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const timeline = await screen.findByLabelText(/Seek to 24:42/);

    fireEvent.change(timeline, { target: { value: "1800" } });
    fireEvent.click(timeline);

    await waitFor(() => {
      expect(fetchMock.mock.calls.map(([url]) => url)).toContain(
        "/api/v1/playback/seek"
      );
    });
    const seekRequest = fetchMock.mock.calls.find(
      ([url]) => url === "/api/v1/playback/seek"
    );
    expect(seekRequest?.[1]?.body).toBe('{"mode":"absolute","seconds":1800}');
  });

  it("shows actionable VLC failure messaging and leaves controls disabled", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = remoteFetch(
      response(
        {
          error: {
            code: "VLC_UNAVAILABLE",
            message: "Remote service found, but VLC is not responding.",
            retryable: true
          }
        },
        503
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("VLC unavailable");
    expect(
      screen.getByText("VLC’s local control interface is not responding on this Mac.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Play playback" })).toBeDisabled();
  });

  it("forgets a rejected pairing token and returns to the pairing state", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        response(
          {
            error: {
              code: "UNAUTHORIZED",
              message: "This phone is not paired with the Mac.",
              retryable: false
            }
          },
          401
        )
      )
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Pair this phone." })
    ).toBeInTheDocument();
    expect(window.localStorage.getItem("mac-vlc-remote.access-token.v1")).toBeNull();
  });

  it("forgets the local pairing token from settings", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = pairedFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const settingsButton = screen.getByRole("button", {
      name: "Open remote settings"
    });
    fireEvent.click(settingsButton);
    expect(await screen.findByRole("dialog", { name: "Remote settings" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Forget this Mac" }));

    expect(
      await screen.findByRole("heading", { name: "Pair this phone." })
    ).toBeInTheDocument();
    expect(window.localStorage.getItem("mac-vlc-remote.access-token.v1")).toBeNull();
  });

  it("keeps secondary actions in a dismissible settings dialog", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    vi.stubGlobal("fetch", pairedFetch());

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Open remote settings" }));

    expect(await screen.findByRole("button", { name: "Stop playback" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Close remote settings" }));
    expect(screen.queryByRole("dialog", { name: "Remote settings" })).not.toBeInTheDocument();
  });
});
