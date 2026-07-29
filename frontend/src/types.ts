export type PlaybackState =
  | "playing"
  | "paused"
  | "stopped"
  | "opening"
  | "buffering"
  | "unknown";

export interface VlcTrack {
  id: string;
  name: string;
  selected: boolean;
}

export interface VlcStatus {
  connection: {
    backend: string;
    vlc: string;
  };
  state: PlaybackState;
  media: {
    title: string | null;
    filename: string | null;
  };
  time: {
    elapsedSeconds: number;
    durationSeconds: number | null;
    position: number | null;
  };
  audio: {
    volumePercent: number;
    muted: boolean;
  };
  playbackRate: number;
  tracks: {
    audio: readonly VlcTrack[];
    subtitles: readonly VlcTrack[];
  };
  capabilities: {
    seek: boolean;
    volume: boolean;
    rate: boolean;
    audioTrackSelection: boolean;
    subtitleTrackSelection: boolean;
    fullscreen: boolean;
    playlistNavigation: boolean;
  };
  updatedAt: string;
}

export type ConnectionState =
  | "connecting"
  | "online"
  | "vlc-unavailable"
  | "unauthenticated"
  | "offline"
  | "server-error";
