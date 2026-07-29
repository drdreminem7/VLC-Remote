const WIKIMEDIA_API = "https://en.wikipedia.org/w/api.php";

type SearchPage = {
  thumbnail?: {
    source?: unknown;
  };
};

type SearchResponse = {
  query?: {
    pages?: Record<string, SearchPage>;
  };
};

const posterCache = new Map<string, string>();

function isSearchResponse(value: unknown): value is SearchResponse {
  return typeof value === "object" && value !== null;
}

function posterFromResponse(value: unknown): string | null {
  if (!isSearchResponse(value) || value.query?.pages === undefined) {
    return null;
  }

  for (const page of Object.values(value.query.pages)) {
    const source = page.thumbnail?.source;
    if (typeof source === "string" && source.startsWith("https://upload.wikimedia.org/")) {
      return source;
    }
  }

  return null;
}

export async function lookupMoviePoster(
  title: string,
  signal?: AbortSignal
): Promise<string | null> {
  const query = title.trim();
  if (!query) {
    return null;
  }

  const cachedPoster = posterCache.get(query);
  if (cachedPoster !== undefined) {
    return cachedPoster;
  }

  const parameters = new URLSearchParams({
    action: "query",
    format: "json",
    generator: "search",
    gsrnamespace: "0",
    gsrsearch: query,
    gsrlimit: "3",
    origin: "*",
    pithumbsize: "640",
    piprop: "thumbnail",
    prop: "pageimages"
  });

  try {
    const response = await fetch(`${WIKIMEDIA_API}?${parameters.toString()}`, {
      headers: { Accept: "application/json" },
      ...(signal === undefined ? {} : { signal })
    });
    if (!response.ok) {
      return null;
    }

    const poster = posterFromResponse(await response.json().catch(() => null));
    if (poster !== null) {
      posterCache.set(query, poster);
    }
    return poster;
  } catch {
    return null;
  }
}
