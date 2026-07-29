import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../src/App";

describe("application shell", () => {
  it("renders the secured Phase 2 connection and honest VLC state", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Ready when VLC is." })
    ).toBeInTheDocument();
    expect(screen.getByText("Backend secured")).toBeInTheDocument();
    expect(screen.getByText("VLC setup paused")).toBeInTheDocument();
    expect(screen.getByText("Phase 2 API ready")).toBeInTheDocument();
  });

  it("keeps every preview control semantic and unavailable", () => {
    render(<App />);

    expect(
      screen.getByRole("button", { name: "Play — VLC unavailable" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: "Skip backward 10 seconds — VLC unavailable"
      })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: "Skip forward 10 seconds — VLC unavailable"
      })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Mute — VLC unavailable" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Volume up — unavailable" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Playback speed — VLC unavailable" })
    ).toBeDisabled();
  });
});
