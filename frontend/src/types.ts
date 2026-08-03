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

export interface LibraryMovie {
  id: string;
  title: string;
  artworkQuery: string;
}

export interface MovieLibraryResponse {
  movies: readonly LibraryMovie[];
}

export interface FolderSubtitle {
  id: string;
  name: string;
}

export interface MovieSubtitlesResponse {
  movieId: string;
  subtitles: readonly FolderSubtitle[];
}

export interface OnlineSubtitle {
  id: string;
  filename: string;
  language: string;
  release: string | null;
  downloads: number;
  trusted: boolean;
  hearingImpaired: boolean;
  moviehashMatch: boolean;
  releaseMatch: boolean;
}

export interface OnlineSubtitlesResponse {
  movieId: string;
  language: string;
  subtitles: readonly OnlineSubtitle[];
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
  subtitleDelaySeconds: number;
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
  fullscreen: boolean;
  updatedAt: string;
}

export type ConnectionState =
  | "connecting"
  | "online"
  | "vlc-unavailable"
  | "unauthenticated"
  | "offline"
  | "server-error";
