import type { VlcStatus } from "../types";

interface ErrorPayload {
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
}

export class RemoteApiError extends Error {
  readonly code: string;
  readonly retryable: boolean;
  readonly status: number;

  constructor(
    message: string,
    { code, retryable, status }: { code: string; retryable: boolean; status: number }
  ) {
    super(message);
    this.name = "RemoteApiError";
    this.code = code;
    this.retryable = retryable;
    this.status = status;
  }
}

export interface RemoteApi {
  getStatus(signal?: AbortSignal): Promise<VlcStatus>;
  togglePlayback(signal?: AbortSignal): Promise<VlcStatus>;
  play(signal?: AbortSignal): Promise<VlcStatus>;
  pause(signal?: AbortSignal): Promise<VlcStatus>;
  stop(signal?: AbortSignal): Promise<VlcStatus>;
  seekAbsolute(seconds: number, signal?: AbortSignal): Promise<VlcStatus>;
  seekRelative(seconds: number, signal?: AbortSignal): Promise<VlcStatus>;
  setVolume(percent: number, signal?: AbortSignal): Promise<VlcStatus>;
  setMuted(muted: boolean, signal?: AbortSignal): Promise<VlcStatus>;
  setRate(rate: number, signal?: AbortSignal): Promise<VlcStatus>;
  selectAudioTrack(trackId: string, signal?: AbortSignal): Promise<VlcStatus>;
  selectSubtitleTrack(trackId: string, signal?: AbortSignal): Promise<VlcStatus>;
  nextItem(signal?: AbortSignal): Promise<VlcStatus>;
  previousItem(signal?: AbortSignal): Promise<VlcStatus>;
}

type FetchImplementation = typeof fetch;

function isErrorPayload(value: unknown): value is ErrorPayload {
  return typeof value === "object" && value !== null;
}

export function createRemoteApi(
  accessToken: string,
  fetchImplementation: FetchImplementation = window.fetch.bind(window)
): RemoteApi {
  async function request(
    path: string,
    options: RequestInit = {}
  ): Promise<VlcStatus> {
    const headers = new Headers(options.headers);
    headers.set("Authorization", `Bearer ${accessToken}`);
    headers.set("Accept", "application/json");
    if (options.body !== undefined) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetchImplementation(`/api/v1${path}`, {
      ...options,
      credentials: "same-origin",
      headers
    });
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const apiError = isErrorPayload(payload) ? payload.error : undefined;
      throw new RemoteApiError(
        apiError?.message ?? "The Mac remote could not complete that request.",
        {
          code: apiError?.code ?? "INTERNAL_ERROR",
          retryable: apiError?.retryable ?? response.status >= 500,
          status: response.status
        }
      );
    }

    return payload as VlcStatus;
  }

  function post(path: string, body?: object, signal?: AbortSignal): Promise<VlcStatus> {
    return request(path, {
      method: "POST",
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      ...(signal === undefined ? {} : { signal })
    });
  }

  return {
    getStatus: (signal) =>
      request("/status", signal === undefined ? {} : { signal }),
    togglePlayback: (signal) => post("/playback/toggle", undefined, signal),
    play: (signal) => post("/playback/play", undefined, signal),
    pause: (signal) => post("/playback/pause", undefined, signal),
    stop: (signal) => post("/playback/stop", undefined, signal),
    seekAbsolute: (seconds, signal) =>
      post("/playback/seek", { mode: "absolute", seconds }, signal),
    seekRelative: (seconds, signal) =>
      post("/playback/seek", { mode: "relative", seconds }, signal),
    setVolume: (percent, signal) => post("/audio/volume", { percent }, signal),
    setMuted: (muted, signal) => post("/audio/mute", { muted }, signal),
    setRate: (rate, signal) => post("/playback/rate", { rate }, signal),
    selectAudioTrack: (trackId, signal) =>
      post("/tracks/audio", { trackId }, signal),
    selectSubtitleTrack: (trackId, signal) =>
      post("/tracks/subtitle", { trackId }, signal),
    nextItem: (signal) => post("/playback/next", undefined, signal),
    previousItem: (signal) => post("/playback/previous", undefined, signal)
  };
}
