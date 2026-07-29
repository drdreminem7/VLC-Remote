import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App";

const TOKEN = "t".repeat(43);

const pausedStatus = {
  connection: { backend: "online", vlc: "online" },
  state: "paused",
  media: { title: "Moonrise, Chapter Four", filename: "moonrise.mkv" },
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

function pairedFetch(): ReturnType<typeof vi.fn<typeof fetch>> {
  return vi.fn<typeof fetch>().mockResolvedValue(response(pausedStatus));
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
      expect(
        screen.getByRole("heading", { name: "Moonrise, Chapter Four" })
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent("Connected");
    expect(screen.getByRole("button", { name: "Play playback" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Skip backward 10 seconds" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Skip forward 10 seconds" })).toBeEnabled();
    expect(screen.getByLabelText(/Volume68%/)).toHaveAttribute("max", "200");
    expect(screen.queryByText("moonrise.mkv")).not.toBeInTheDocument();
    expect(screen.queryByText("Local API protected")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/status",
      expect.objectContaining({ credentials: "same-origin" })
    );
  });

  it("sends one fixed toggle request and refreshes status after success", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const playingStatus = { ...pausedStatus, state: "playing" };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response(pausedStatus))
      .mockResolvedValueOnce(response(playingStatus))
      .mockResolvedValueOnce(response(playingStatus));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const playButton = await screen.findByRole("button", { name: "Play playback" });

    fireEvent.click(playButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Pause playback" })).toBeEnabled();
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/status",
      "/api/v1/playback/toggle",
      "/api/v1/status"
    ]);
  });

  it("keeps controls active while a command is being confirmed", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    let resolveCommand: ((value: Response) => void) | undefined;
    const commandResponse = new Promise<Response>((resolve) => {
      resolveCommand = resolve;
    });
    const playingStatus = { ...pausedStatus, state: "playing" };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(response(pausedStatus))
      .mockReturnValueOnce(commandResponse)
      .mockResolvedValueOnce(response(playingStatus));
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

  it("previews timeline movement and only seeks when the control is released", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = pairedFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const timeline = await screen.findByLabelText(/Seek to 24:42/);

    fireEvent.change(timeline, { target: { value: "1800" } });
    expect(screen.getByText("30:00")).toBeInTheDocument();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(["/api/v1/status"]);

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

  it("shows actionable VLC failure messaging and leaves controls disabled", async () => {
    window.localStorage.setItem("mac-vlc-remote.access-token.v1", TOKEN);
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
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
