import { afterEach, describe, expect, it, vi } from "vitest";

import { lookupMoviePoster } from "../src/api/poster";

function requestUrl(input: Parameters<typeof fetch>[0]): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("movie poster lookup", () => {
  it("returns a same-origin poster payload for a matching title", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          imageData: "data:image/jpeg;base64,"
        })
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(lookupMoviePoster("The Quiet Film", "t".repeat(43))).resolves.toBe(
      "data:image/jpeg;base64,"
    );
    const [request] = fetchMock.mock.calls[0] ?? [];
    if (request === undefined) {
      throw new Error("Poster lookup did not make a request");
    }
    expect(requestUrl(request)).toContain("/api/v1/artwork?title=The+Quiet+Film");
    const init = fetchMock.mock.calls[0]?.[1];
    if (init === undefined) {
      throw new Error("Poster lookup did not include request options");
    }
    expect(new Headers(init.headers).get("Authorization")).toBe(
      `Bearer ${"t".repeat(43)}`
    );
  });

  it("returns no artwork when the search has no thumbnail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(JSON.stringify({ query: { pages: {} } }))
      )
    );

    await expect(lookupMoviePoster("Film Without Artwork", "t".repeat(43))).resolves.toBeNull();
  });
});
