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
  it("returns a Wikimedia thumbnail for a matching title", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: {
            pages: {
              "42": {
                thumbnail: {
                  source: "https://upload.wikimedia.org/wikipedia/poster.jpg"
                }
              }
            }
          }
        })
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(lookupMoviePoster("The Quiet Film")).resolves.toBe(
      "https://upload.wikimedia.org/wikipedia/poster.jpg"
    );
    const [request] = fetchMock.mock.calls[0] ?? [];
    if (request === undefined) {
      throw new Error("Poster lookup did not make a request");
    }
    expect(requestUrl(request)).toContain("pithumbsize=640");
    expect(requestUrl(request)).toContain("gsrsearch=The+Quiet+Film");
  });

  it("returns no artwork when the search has no thumbnail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(
        new Response(JSON.stringify({ query: { pages: {} } }))
      )
    );

    await expect(lookupMoviePoster("Film Without Artwork")).resolves.toBeNull();
  });
});
