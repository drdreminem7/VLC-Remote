import {
  forgetStoredAccessToken,
  getInitialAccessToken,
  getStoredAccessToken,
  isValidAccessToken,
  storeAccessToken,
  takePairingTokenFromFragment
} from "../src/auth";
import { afterEach, describe, expect, it } from "vitest";

const TOKEN = "a".repeat(43);

afterEach(() => {
  window.localStorage.clear();
  window.history.replaceState(null, document.title, "/");
});

describe("pairing token storage", () => {
  it("accepts URL-safe, sufficiently long pairing tokens only", () => {
    expect(isValidAccessToken(TOKEN)).toBe(true);
    expect(isValidAccessToken("short-token")).toBe(false);
    expect(isValidAccessToken("a".repeat(31))).toBe(false);
    expect(isValidAccessToken("a".repeat(32) + "+")).toBe(false);
  });

  it("stores a valid fragment token and removes it from the visible URL", () => {
    window.history.replaceState(null, document.title, `/#token=${TOKEN}`);

    expect(takePairingTokenFromFragment()).toBe(TOKEN);
    expect(window.location.hash).toBe("");
    expect(storeAccessToken(TOKEN)).toBe(true);
    expect(getStoredAccessToken()).toBe(TOKEN);
  });

  it("uses a pairing fragment before a previous local token", () => {
    storeAccessToken("b".repeat(43));
    window.history.replaceState(null, document.title, `/#token=${TOKEN}`);

    expect(getInitialAccessToken()).toBe(TOKEN);
    expect(getStoredAccessToken()).toBe(TOKEN);
    expect(window.location.hash).toBe("");
  });

  it("forgets the token without touching other origin storage", () => {
    window.localStorage.setItem("unrelated", "keep");
    storeAccessToken(TOKEN);

    forgetStoredAccessToken();

    expect(getStoredAccessToken()).toBeNull();
    expect(window.localStorage.getItem("unrelated")).toBe("keep");
  });
});
