import { expect, test, type Page } from "@playwright/test";

const TOKEN = "e".repeat(43);

const pausedStatus = {
  connection: { backend: "online", vlc: "online" },
  state: "paused",
  media: { title: "Moonrise, Chapter Four", filename: "moonrise.mkv" },
  time: { elapsedSeconds: 1482, durationSeconds: 6420, position: 0.23 },
  audio: { volumePercent: 68, muted: false },
  playbackRate: 1,
  tracks: { audio: [], subtitles: [] },
  capabilities: {
    seek: true,
    volume: true,
    rate: true,
    audioTrackSelection: false,
    subtitleTrackSelection: false,
    fullscreen: false,
    playlistNavigation: false
  },
  updatedAt: "2026-07-29T12:00:00Z"
};

async function mockOnlineStatus(page: Page) {
  await page.route("**/api/v1/status", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) })
  );
}

async function expectNoPressedColorFlash(page: Page, name: string) {
  const button = page.getByRole("button", { name });
  const before = await button.evaluate((element) => getComputedStyle(element).backgroundColor);
  const box = await button.boundingBox();
  if (box === null) {
    throw new Error(`Could not measure ${name}`);
  }

  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  expect(await button.evaluate((element) => getComputedStyle(element).backgroundColor)).toBe(before);
  await page.mouse.up();
}

test("pairs from a fragment and forgets the Mac", async ({ page }) => {
  await mockOnlineStatus(page);

  await page.goto(`/#token=${TOKEN}`);

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Moonrise, Chapter Four" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Skip backward 10 seconds" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Skip forward 10 seconds" })).toBeVisible();
  await expect(page.getByText("moonrise.mkv")).toHaveCount(0);
  await expect(page.getByText("Local API protected")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.scrollingElement?.scrollHeight === window.innerHeight
    )
  ).toBe(true);
  await page.getByRole("button", { name: "Open remote settings" }).click();
  await expect(page.getByRole("dialog", { name: "Remote settings" })).toBeVisible();
  await page.getByRole("button", { name: "Forget this Mac" }).click();

  await expect(page.getByRole("heading", { name: "Pair this phone." })).toBeVisible();
});

test("previews a timeline drag and sends exactly one seek on release", async ({ page }) => {
  let seekRequests = 0;
  await page.route("**/api/v1/status", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) })
  );
  await page.route("**/api/v1/playback/seek", async (route) => {
    seekRequests += 1;
    expect(route.request().postDataJSON()).toEqual({ mode: "absolute", seconds: 1800 });
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) });
  });

  await page.goto(`/#token=${TOKEN}`);
  const timeline = page.locator("#seek-timeline");
  await timeline.evaluate((element) => {
    const input = element as HTMLInputElement;
    const setter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value"
    )?.set;
    setter?.call(input, "1800");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(page.getByText("30:00", { exact: true })).toBeVisible();
  expect(seekRequests).toBe(0);

  await timeline.dispatchEvent("pointerup");
  await expect.poll(() => seekRequests).toBe(1);
});

test("keeps transport and mute button colors stable while pressed", async ({ page }) => {
  await mockOnlineStatus(page);
  await page.route("**/api/v1/playback/toggle", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) })
  );
  await page.route("**/api/v1/playback/seek", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) })
  );
  await page.route("**/api/v1/audio/mute", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) })
  );

  await page.goto(`/#token=${TOKEN}`);
  await expectNoPressedColorFlash(page, "Play playback");
  await expectNoPressedColorFlash(page, "Skip backward 10 seconds");
  await expectNoPressedColorFlash(page, "Mute audio");
});

test("recovers from a temporary backend failure", async ({ page }) => {
  let requests = 0;
  await page.route("**/api/v1/status", (route) => {
    requests += 1;
    if (requests <= 2) {
      return route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "VLC_UNAVAILABLE",
            message: "Remote service found, but VLC is not responding.",
            retryable: true
          }
        })
      });
    }
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(pausedStatus) });
  });

  await page.goto(`/#token=${TOKEN}`);
  await expect(page.getByRole("alert")).toContainText("VLC unavailable");
  await expect(
    page.getByText("VLC’s local control interface is not responding on this Mac.")
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Moonrise, Chapter Four" })).toBeVisible({
    timeout: 4000
  });
});

test("forgets an authentication-rejected pairing token", async ({ page }) => {
  await page.route("**/api/v1/status", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "UNAUTHORIZED",
          message: "This phone is not paired with the Mac.",
          retryable: false
        }
      })
    })
  );

  await page.goto(`/#token=${TOKEN}`);

  await expect(page.getByRole("heading", { name: "Pair this phone." })).toBeVisible();
});
