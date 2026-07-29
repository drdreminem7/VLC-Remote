import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createRemoteApi,
  type RemoteApi,
  RemoteApiError
} from "../api/client";
import {
  forgetStoredAccessToken,
  getInitialAccessToken
} from "../auth";
import type { ConnectionState, VlcStatus } from "../types";

const VISIBLE_POLL_MS = 900;
const HIDDEN_POLL_MS = 6000;
const MAX_RETRY_MS = 30000;

export interface RemoteState {
  connection: ConnectionState;
  status: VlcStatus | null;
  message: string;
  pendingAction: string | null;
  token: string | null;
  forgetPairing(): void;
  togglePlayback(): Promise<void>;
  play(): Promise<void>;
  pause(): Promise<void>;
  stop(): Promise<void>;
  seekAbsolute(seconds: number): Promise<VlcStatus | null>;
  seekRelative(seconds: number): Promise<void>;
  setVolume(percent: number): Promise<void>;
  setMuted(muted: boolean): Promise<void>;
  setRate(rate: number): Promise<void>;
  selectAudioTrack(trackId: string): Promise<void>;
  selectSubtitleTrack(trackId: string): Promise<void>;
  nextItem(): Promise<void>;
  previousItem(): Promise<void>;
}

function describeConnection(connection: ConnectionState): string {
  switch (connection) {
    case "online":
      return "Mac and VLC connected";
    case "connecting":
      return "Looking for your Mac remote…";
    case "vlc-unavailable":
      return "Remote service found, but VLC is not responding.";
    case "unauthenticated":
      return "This phone is not paired with the Mac.";
    case "offline":
      return "This phone is offline. Reconnect to your home network.";
    case "server-error":
      return "The Mac remote could not be reached. Check your home network.";
  }
}

function connectionFromError(error: unknown): ConnectionState {
  if (error instanceof RemoteApiError) {
    if (error.code === "UNAUTHORIZED") {
      return "unauthenticated";
    }
    if (error.code === "VLC_UNAVAILABLE") {
      return "vlc-unavailable";
    }
  }
  return "server-error";
}

function retryDelay(failures: number): number {
  return Math.min(1000 * 2 ** Math.max(0, failures - 1), MAX_RETRY_MS);
}

export function useRemote(): RemoteState {
  const [token, setToken] = useState<string | null>(() => getInitialAccessToken());
  const [connection, setConnection] = useState<ConnectionState>(() =>
    token === null ? "unauthenticated" : "connecting"
  );
  const [status, setStatus] = useState<VlcStatus | null>(null);
  const [message, setMessage] = useState(() =>
    describeConnection(token === null ? "unauthenticated" : "connecting")
  );
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const commandControllerRef = useRef<AbortController | null>(null);
  const commandBusyRef = useRef(false);
  const statusRef = useRef<VlcStatus | null>(null);

  const api = useMemo<RemoteApi | null>(
    () => (token === null ? null : createRemoteApi(token)),
    [token]
  );

  const applyStatus = useCallback((nextStatus: VlcStatus) => {
    statusRef.current = nextStatus;
    setStatus(nextStatus);
    setConnection("online");
    setMessage(describeConnection("online"));
  }, []);

  useEffect(() => {
    if (api === null) {
      return undefined;
    }

    let disposed = false;
    let polling = false;
    let failures = 0;
    let pollTimer: number | undefined;
    let pollController: AbortController | null = null;
    let restartAfterPoll: number | null = null;

    const cancelTimer = () => {
      if (pollTimer !== undefined) {
        window.clearTimeout(pollTimer);
        pollTimer = undefined;
      }
    };

    const schedule = (delay: number) => {
      cancelTimer();
      if (!disposed) {
        pollTimer = window.setTimeout(() => {
          void poll();
        }, delay);
      }
    };

    const poll = async () => {
      if (disposed || polling) {
        return;
      }
      if (!navigator.onLine) {
        setConnection("offline");
        setMessage(describeConnection("offline"));
        schedule(HIDDEN_POLL_MS);
        return;
      }

      polling = true;
      pollController = new AbortController();
      if (statusRef.current === null) {
        setConnection("connecting");
        setMessage(describeConnection("connecting"));
      }

      try {
        const nextStatus = await api.getStatus(pollController.signal);
        if (disposed) {
          return;
        }
        failures = 0;
        applyStatus(nextStatus);
        schedule(document.visibilityState === "hidden" ? HIDDEN_POLL_MS : VISIBLE_POLL_MS);
      } catch (error) {
        if (disposed || (error instanceof DOMException && error.name === "AbortError")) {
          return;
        }
        failures += 1;
        const nextConnection = connectionFromError(error);
        if (nextConnection === "unauthenticated") {
          forgetStoredAccessToken();
          statusRef.current = null;
          setStatus(null);
          setToken(null);
          setConnection("unauthenticated");
          setMessage(describeConnection("unauthenticated"));
          return;
        }
        setConnection(nextConnection);
        setMessage(
          error instanceof RemoteApiError
            ? error.message
            : describeConnection(nextConnection)
        );
        schedule(Math.max(
          document.visibilityState === "hidden" ? HIDDEN_POLL_MS : 0,
          retryDelay(failures)
        ));
      } finally {
        polling = false;
        pollController = null;
        if (restartAfterPoll !== null) {
          const delay = restartAfterPoll;
          restartAfterPoll = null;
          schedule(delay);
        }
      }
    };

    const restartPolling = () => {
      if (disposed) {
        return;
      }
      pollController?.abort();
      const delay = document.visibilityState === "hidden" ? HIDDEN_POLL_MS : 0;
      if (polling) {
        restartAfterPoll = delay;
      } else {
        schedule(delay);
      }
    };

    const handleOffline = () => {
      pollController?.abort();
      setConnection("offline");
      setMessage(describeConnection("offline"));
      if (polling) {
        restartAfterPoll = HIDDEN_POLL_MS;
      } else {
        schedule(HIDDEN_POLL_MS);
      }
    };

    window.addEventListener("online", restartPolling);
    window.addEventListener("offline", handleOffline);
    document.addEventListener("visibilitychange", restartPolling);
    void poll();

    return () => {
      disposed = true;
      cancelTimer();
      pollController?.abort();
      window.removeEventListener("online", restartPolling);
      window.removeEventListener("offline", handleOffline);
      document.removeEventListener("visibilitychange", restartPolling);
    };
  }, [api, applyStatus]);

  useEffect(
    () => () => {
      commandControllerRef.current?.abort();
    },
    []
  );

  const runCommand = useCallback(
    async (
      action: string,
      command: (activeApi: RemoteApi, signal: AbortSignal) => Promise<VlcStatus>
    ): Promise<VlcStatus | null> => {
      if (api === null || commandBusyRef.current || !navigator.onLine) {
        return null;
      }

      commandControllerRef.current?.abort();
      const controller = new AbortController();
      commandControllerRef.current = controller;
      commandBusyRef.current = true;
      setPendingAction(action);

      try {
        const nextStatus = await command(api, controller.signal);
        applyStatus(nextStatus);
        return nextStatus;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return null;
        }
        const nextConnection = connectionFromError(error);
        if (nextConnection === "unauthenticated") {
          forgetStoredAccessToken();
          setToken(null);
          statusRef.current = null;
          setStatus(null);
        }
        setConnection(nextConnection);
        setMessage(
          error instanceof RemoteApiError
            ? error.message
            : describeConnection(nextConnection)
        );
        return null;
      } finally {
        if (commandControllerRef.current === controller) {
          commandControllerRef.current = null;
          commandBusyRef.current = false;
          setPendingAction(null);
        }
      }
    },
    [api, applyStatus]
  );

  const forgetPairing = useCallback(() => {
    commandControllerRef.current?.abort();
    commandBusyRef.current = false;
    forgetStoredAccessToken();
    setToken(null);
    statusRef.current = null;
    setStatus(null);
    setPendingAction(null);
    setConnection("unauthenticated");
    setMessage(describeConnection("unauthenticated"));
  }, []);

  return {
    connection,
    status,
    message,
    pendingAction,
    token,
    forgetPairing,
    togglePlayback: () =>
      runCommand("toggle", (activeApi, signal) => activeApi.togglePlayback(signal)).then(
        () => undefined
      ),
    play: () =>
      runCommand("play", (activeApi, signal) => activeApi.play(signal)).then(
        () => undefined
      ),
    pause: () =>
      runCommand("pause", (activeApi, signal) => activeApi.pause(signal)).then(
        () => undefined
      ),
    stop: () =>
      runCommand("stop", (activeApi, signal) => activeApi.stop(signal)).then(
        () => undefined
      ),
    seekAbsolute: (seconds) =>
      runCommand("seek", (activeApi, signal) => activeApi.seekAbsolute(seconds, signal)),
    seekRelative: (seconds) =>
      runCommand("seek", (activeApi, signal) => activeApi.seekRelative(seconds, signal)).then(
        () => undefined
      ),
    setVolume: (percent) =>
      runCommand("volume", (activeApi, signal) => activeApi.setVolume(percent, signal)).then(
        () => undefined
      ),
    setMuted: (muted) =>
      runCommand("mute", (activeApi, signal) => activeApi.setMuted(muted, signal)).then(
        () => undefined
      ),
    setRate: (rate) =>
      runCommand("rate", (activeApi, signal) => activeApi.setRate(rate, signal)).then(
        () => undefined
      ),
    selectAudioTrack: (trackId) =>
      runCommand("audio-track", (activeApi, signal) =>
        activeApi.selectAudioTrack(trackId, signal)
      ).then(() => undefined),
    selectSubtitleTrack: (trackId) =>
      runCommand("subtitle-track", (activeApi, signal) =>
        activeApi.selectSubtitleTrack(trackId, signal)
      ).then(() => undefined),
    nextItem: () =>
      runCommand("next", (activeApi, signal) => activeApi.nextItem(signal)).then(
        () => undefined
      ),
    previousItem: () =>
      runCommand("previous", (activeApi, signal) => activeApi.previousItem(signal)).then(
        () => undefined
      )
  };
}
