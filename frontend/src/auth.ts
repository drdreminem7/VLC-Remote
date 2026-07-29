const TOKEN_STORAGE_KEY = "mac-vlc-remote.access-token.v1";
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,512}$/;

function canUseStorage(): boolean {
  try {
    const key = "__mac_vlc_remote_storage_probe__";
    window.localStorage.setItem(key, "1");
    window.localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function isValidAccessToken(value: string | null): value is string {
  return value !== null && TOKEN_PATTERN.test(value);
}

export function getStoredAccessToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }

  const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  return isValidAccessToken(token) ? token : null;
}

export function storeAccessToken(token: string): boolean {
  if (!isValidAccessToken(token) || !canUseStorage()) {
    return false;
  }

  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  return true;
}

export function forgetStoredAccessToken(): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function clearPairingFragment(): void {
  window.history.replaceState(
    null,
    document.title,
    `${window.location.pathname}${window.location.search}`
  );
}

export function takePairingTokenFromFragment(): string | null {
  const fragment = window.location.hash.slice(1);
  if (!fragment) {
    return null;
  }

  const parameters = new URLSearchParams(fragment);
  const token = parameters.get("token") ??
    (fragment.includes("=") ? null : fragment);

  if (parameters.has("token") || token !== null) {
    clearPairingFragment();
  }

  return isValidAccessToken(token) ? token : null;
}

export function getInitialAccessToken(): string | null {
  const pairingToken = takePairingTokenFromFragment();
  if (pairingToken !== null) {
    storeAccessToken(pairingToken);
    return pairingToken;
  }
  return getStoredAccessToken();
}
