import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../src/App";

describe("application shell", () => {
  it("renders the Phase 1 connection and media state", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Your Mac, within reach." })
    ).toBeInTheDocument();
    expect(screen.getByText("Remote service ready")).toBeInTheDocument();
    expect(screen.getByText("VLC connection not configured")).toBeInTheDocument();
  });

  it("keeps playback preview controls semantic and unavailable", () => {
    render(<App />);

    expect(
      screen.getByRole("button", { name: "Play — unavailable" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: "Skip backward 10 seconds — unavailable"
      })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", {
        name: "Skip forward 10 seconds — unavailable"
      })
    ).toBeDisabled();
  });
});
