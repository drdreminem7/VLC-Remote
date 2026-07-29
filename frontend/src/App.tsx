import { useEffect, useMemo, useRef, useState } from "react";

import { useRemote } from "./hooks/useRemote";
import type { ConnectionState, VlcStatus } from "./types";
import { clamp, formatDuration } from "./utils/time";

const DEFAULT_RATES = [0.5, 0.75, 1, 1.25, 1.5, 2];

function StatusDot() {
  return <span className="status-dot" aria-hidden="true" />;
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m6.75 6.75 10.5 10.5m0-10.5-10.5 10.5" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7.3 7.3 0 0 0-.1-1.2l2-1.55-2-3.45-2.45 1a7 7 0 0 0-2.05-1.2L14 3h-4l-.4 2.6a7 7 0 0 0-2.05 1.2l-2.45-1-2 3.45 2 1.55A7.3 7.3 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.55 2 3.45 2.45-1a7 7 0 0 0 2.05 1.2L10 21h4l.4-2.6a7 7 0 0 0 2.05-1.2l2.45 1 2-3.45-2-1.55c.07-.4.1-.8.1-1.2Z" />
    </svg>
  );
}

function RewindIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M11.5 7 5 12l6.5 5V7Zm7.5 0-6.5 5 6.5 5V7Z" />
    </svg>
  );
}

function ForwardIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m12.5 7 6.5 5-6.5 5V7ZM5 7l6.5 5L5 17V7Z" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m8.25 5.75 10 6.25-10 6.25V5.75Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M7 5.5h3.5v13H7v-13Zm6.5 0H17v13h-3.5v-13Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <rect x="6.5" y="6.5" width="11" height="11" rx="1.5" />
    </svg>
  );
}

function VolumeIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4.5 10v4h3l4 3.5v-11l-4 3.5h-3Z" />
      <path d="M15 9.25a4.25 4.25 0 0 1 0 5.5M17.5 6.75a7.75 7.75 0 0 1 0 10.5" />
    </svg>
  );
}

function MuteIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4.5 10v4h3l4 3.5v-11l-4 3.5h-3Z" />
      <path d="m16 10 4 4m0-4-4 4" />
    </svg>
  );
}

function SpeedIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 16a8 8 0 1 1 14 0" />
      <path d="m12 13 4-4" />
      <path d="M8 18h8" />
    </svg>
  );
}

function connectionLabel(connection: ConnectionState): string {
  switch (connection) {
    case "online":
      return "Connected";
    case "connecting":
      return "Connecting";
    case "vlc-unavailable":
      return "VLC unavailable";
    case "unauthenticated":
      return "Pair this phone";
    case "offline":
      return "Phone offline";
    case "server-error":
      return "Mac unavailable";
  }
}

function mediaHeading(status: VlcStatus | null, connection: ConnectionState): string {
  if (status?.media.title) {
    return status.media.title;
  }
  if (connection === "unauthenticated") {
    return "Pair this phone.";
  }
  if (connection === "vlc-unavailable") {
    return "VLC is unavailable.";
  }
  if (connection === "offline") {
    return "You’re offline.";
  }
  return "Waiting for your Mac.";
}

function mediaDescription(status: VlcStatus | null, connection: ConnectionState): string {
  if (status !== null) {
    return status.state === "playing" ? "Playing" : "Paused";
  }
  if (connection === "unauthenticated") {
    return "Open the pairing link from your Mac to connect this phone.";
  }
  if (connection === "vlc-unavailable") {
    return "VLC’s local control interface is not responding on this Mac.";
  }
  return "The remote will reconnect automatically when the Mac is available.";
}

export default function App() {
  const remote = useRemote();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [seekPreview, setSeekPreview] = useState<number | null>(null);
  const [volumePreview, setVolumePreview] = useState<number | null>(null);
  const seekingRef = useRef(false);
  const seekPreviewRef = useRef<number | null>(null);
  const adjustingVolumeRef = useRef(false);
  const volumePreviewRef = useRef<number | null>(null);

  const status = remote.status;
  const isConnected = remote.connection === "online" && status !== null;
  const controlsEnabled = isConnected;
  const duration = status?.time.durationSeconds ?? null;
  const canSeek = controlsEnabled && status?.capabilities.seek === true && duration !== null && duration > 0;
  const canAdjustVolume = controlsEnabled && status?.capabilities.volume === true;
  const canAdjustRate = controlsEnabled && status?.capabilities.rate === true;
  const currentElapsed = status?.time.elapsedSeconds ?? 0;
  const displayedElapsed = seekPreview ?? currentElapsed;
  const displayedVolume = volumePreview ?? status?.audio.volumePercent ?? 0;
  const playbackRates = useMemo(
    () =>
      Array.from(new Set([...DEFAULT_RATES, status?.playbackRate ?? 1])).sort(
        (first, second) => first - second
      ),
    [status?.playbackRate]
  );

  useEffect(() => {
    if (!seekingRef.current) {
      setSeekPreview(null);
      seekPreviewRef.current = null;
    }
  }, [status?.time.elapsedSeconds]);

  useEffect(() => {
    if (!adjustingVolumeRef.current) {
      setVolumePreview(null);
      volumePreviewRef.current = null;
    }
  }, [status?.audio.volumePercent]);

  useEffect(() => {
    if (!settingsOpen) {
      return undefined;
    }

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSettingsOpen(false);
      }
    };

    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [settingsOpen]);

  const beginSeeking = () => {
    if (!canSeek) {
      return;
    }
    seekingRef.current = true;
    const initialValue = clamp(currentElapsed, 0, duration ?? 0);
    seekPreviewRef.current = initialValue;
    setSeekPreview(initialValue);
  };

  const commitSeek = () => {
    if (!seekingRef.current || seekPreviewRef.current === null) {
      return;
    }
    const target = seekPreviewRef.current;
    seekingRef.current = false;
    seekPreviewRef.current = null;
    setSeekPreview(null);
    void remote.seekAbsolute(target);
  };

  const beginVolumeAdjustment = () => {
    if (!canAdjustVolume) {
      return;
    }
    adjustingVolumeRef.current = true;
    const initialValue = clamp(status?.audio.volumePercent ?? 0, 0, 200);
    volumePreviewRef.current = initialValue;
    setVolumePreview(initialValue);
  };

  const commitVolume = () => {
    if (!adjustingVolumeRef.current || volumePreviewRef.current === null) {
      return;
    }
    const target = volumePreviewRef.current;
    adjustingVolumeRef.current = false;
    volumePreviewRef.current = null;
    setVolumePreview(null);
    void remote.setVolume(target);
  };

  const isPlaying = status?.state === "playing";
  const primaryLabel = isPlaying ? "Pause playback" : "Play playback";

  return (
    <main className="experience" id="main-content">
      <section className="remote" aria-label="Mac VLC remote">
        <header className="remote-header">
          <div className="device">
            <span className="device__mark" aria-hidden="true">
              V
            </span>
            <span className="device__copy">
              <strong>Living room Mac</strong>
              <span
                aria-live="polite"
                role={remote.connection === "online" ? "status" : "alert"}
              >
                <StatusDot />
                {connectionLabel(remote.connection)}
              </span>
            </span>
          </div>

          <button
            aria-controls="remote-settings"
            aria-expanded={settingsOpen}
            className="icon-button"
            onClick={() => setSettingsOpen((open) => !open)}
            type="button"
          >
            <SettingsIcon />
            <span className="sr-only">Open remote settings</span>
          </button>
        </header>

        <section className="touch-surface" aria-labelledby="media-title">
          <div className="touch-surface__texture" aria-hidden="true" />
          <div className="touch-surface__content">
            <p className="eyebrow">
              {status === null ? connectionLabel(remote.connection) : status.state}
            </p>
            <h1 id="media-title">{mediaHeading(status, remote.connection)}</h1>
            <p className="touch-surface__message">{mediaDescription(status, remote.connection)}</p>
          </div>

          <div className="timeline" aria-label="Playback timeline">
            <label className="sr-only" htmlFor="seek-timeline">
              Seek to {formatDuration(displayedElapsed)}
            </label>
            <input
              aria-valuetext={`${formatDuration(displayedElapsed)} of ${formatDuration(duration)}`}
              className="range-input range-input--timeline"
              disabled={!canSeek}
              id="seek-timeline"
              max={duration ?? 1}
              min="0"
              onBlur={commitSeek}
              onChange={(event) => {
                const value = Number(event.currentTarget.value);
                seekingRef.current = true;
                seekPreviewRef.current = value;
                setSeekPreview(value);
              }}
              onKeyUp={commitSeek}
              onPointerDown={beginSeeking}
              onPointerUp={commitSeek}
              step="1"
              type="range"
              value={clamp(displayedElapsed, 0, duration ?? 1)}
            />
            <div className="timeline__labels">
              <time>{formatDuration(displayedElapsed)}</time>
              <span>{status === null ? "Waiting for VLC" : status.state}</span>
              <time>{formatDuration(duration)}</time>
            </div>
          </div>
        </section>

        <section className="transport" aria-label="Playback controls">
          <button
            aria-label="Skip backward 10 seconds"
            className="round-button round-button--secondary transport__skip transport__skip--back"
            disabled={!controlsEnabled}
            onClick={() => void remote.seekRelative(-10)}
            type="button"
          >
            <RewindIcon />
          </button>
          <button
            aria-busy={remote.pendingAction === "toggle"}
            aria-label={primaryLabel}
            className="round-button round-button--primary"
            disabled={!controlsEnabled}
            onClick={() => void remote.togglePlayback()}
            type="button"
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>
          <button
            aria-label="Skip forward 10 seconds"
            className="round-button round-button--secondary transport__skip transport__skip--forward"
            disabled={!controlsEnabled}
            onClick={() => void remote.seekRelative(10)}
            type="button"
          >
            <ForwardIcon />
          </button>
        </section>

        <section className="utility-controls" aria-label="Audio and speed controls">
          <button
            aria-label={status?.audio.muted ? "Unmute audio" : "Mute audio"}
            className="utility-button"
            disabled={!canAdjustVolume}
            onClick={() => void remote.setMuted(!(status?.audio.muted ?? false))}
            type="button"
          >
            <MuteIcon />
            <span>{status?.audio.muted ? "Unmute" : "Mute"}</span>
          </button>

          <div className="volume-control">
            <label htmlFor="volume-control">
              <VolumeIcon />
              <span>Volume</span>
              <span className="volume-value">{displayedVolume}%</span>
            </label>
            <input
              className="range-input range-input--volume"
              disabled={!canAdjustVolume}
              id="volume-control"
              max="200"
              min="0"
              onBlur={commitVolume}
              onChange={(event) => {
                const value = Number(event.currentTarget.value);
                adjustingVolumeRef.current = true;
                volumePreviewRef.current = value;
                setVolumePreview(value);
              }}
              onKeyUp={commitVolume}
              onPointerDown={beginVolumeAdjustment}
              onPointerUp={commitVolume}
              step="1"
              type="range"
              value={displayedVolume}
            />
          </div>

          <label className="speed-control" htmlFor="rate-control">
            <SpeedIcon />
            <span>Speed</span>
            <select
              disabled={!canAdjustRate}
              id="rate-control"
              onChange={(event) => void remote.setRate(Number(event.currentTarget.value))}
              value={status?.playbackRate ?? 1}
            >
              {playbackRates.map((rate) => (
                <option key={rate} value={rate}>
                  {rate}×
                </option>
              ))}
            </select>
          </label>
        </section>

      </section>

      {settingsOpen ? (
        <div className="settings-dialog" onMouseDown={() => setSettingsOpen(false)}>
          <section
            aria-label="Remote settings"
            aria-modal="true"
            className="settings-dialog__sheet"
            id="remote-settings"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
          >
            <header className="settings-dialog__header">
              <div>
                <p className="eyebrow">Remote settings</p>
                <h2>Connection & options</h2>
              </div>
              <button
                aria-label="Close remote settings"
                className="icon-button"
                onClick={() => setSettingsOpen(false)}
                type="button"
              >
                <CloseIcon />
              </button>
            </header>

            <p className="settings-dialog__message" aria-live="polite">{remote.message}</p>

            <div className="settings-dialog__actions">
              <button
                aria-label="Stop playback"
                className="icon-stop-button"
                disabled={!controlsEnabled}
                onClick={() => void remote.stop()}
                type="button"
              >
                <StopIcon />
                Stop playback
              </button>
              <button
                className="text-button"
                disabled={remote.token === null}
                onClick={() => remote.forgetPairing()}
                type="button"
              >
                Forget this Mac
              </button>
            </div>

            {status?.capabilities.playlistNavigation ? (
              <section className="advanced-controls" aria-label="Playlist controls">
                <button disabled={!controlsEnabled} onClick={() => void remote.previousItem()} type="button">
                  Previous item
                </button>
                <button disabled={!controlsEnabled} onClick={() => void remote.nextItem()} type="button">
                  Next item
                </button>
              </section>
            ) : null}

            {status?.capabilities.audioTrackSelection || status?.capabilities.subtitleTrackSelection ? (
              <section className="track-controls" aria-label="Available tracks">
                {status.capabilities.audioTrackSelection ? (
                  <label>
                    Audio track
                    <select
                      disabled={!controlsEnabled}
                      onChange={(event) => void remote.selectAudioTrack(event.currentTarget.value)}
                      value={status.tracks.audio.find((track) => track.selected)?.id ?? ""}
                    >
                      {status.tracks.audio.map((track) => (
                        <option key={track.id} value={track.id}>
                          {track.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                {status.capabilities.subtitleTrackSelection ? (
                  <label>
                    Subtitles
                    <select
                      disabled={!controlsEnabled}
                      onChange={(event) => void remote.selectSubtitleTrack(event.currentTarget.value)}
                      value={status.tracks.subtitles.find((track) => track.selected)?.id ?? ""}
                    >
                      {status.tracks.subtitles.map((track) => (
                        <option key={track.id} value={track.id}>
                          {track.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      <aside className="room-note" aria-label="Remote status summary">
        <p className="eyebrow">Mac VLC Remote / 03</p>
        <h2>Stay with the film, not the controls.</h2>
        <p>{remote.message}</p>
        <dl>
          <div>
            <dt>Control layer</dt>
            <dd>{remote.token === null ? "Pairing needed" : "Authenticated"}</dd>
          </div>
          <div>
            <dt>VLC link</dt>
            <dd>{connectionLabel(remote.connection)}</dd>
          </div>
        </dl>
      </aside>
    </main>
  );
}
