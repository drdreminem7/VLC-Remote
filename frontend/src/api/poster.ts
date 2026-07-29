const posterCache = new Map<string, string>();
type ArtworkResponse = { imageData?: unknown };

export async function lookupMoviePoster(
  title: string,
  accessToken: string | null,
  signal?: AbortSignal
): Promise<string | null> {
  const query = title.trim();
  if (!query || accessToken === null) {
    return null;
  }

  const cachedPoster = posterCache.get(query);
  if (cachedPoster !== undefined) {
    return cachedPoster;
  }

  const parameters = new URLSearchParams({ title: query });

  try {
    const response = await fetch(`/api/v1/artwork?${parameters.toString()}`, {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`
      },
      ...(signal === undefined ? {} : { signal })
    });
    if (!response.ok) {
      return null;
    }

    const payload: unknown = await response.json().catch(() => null);
    const imageData =
      typeof payload === "object" && payload !== null
        ? (payload as ArtworkResponse).imageData
        : null;
    const poster =
      typeof imageData === "string" && imageData.startsWith("data:image/")
        ? imageData
        : null;
    if (poster !== null) {
      posterCache.set(query, poster);
    }
    return poster;
  } catch {
    return null;
  }
}
