import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function respondWith(status: number, body: unknown) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

describe("App", () => {
  afterEach(cleanup);

  it("says that everything is ready when the api is ready", async () => {
    respondWith(200, { status: "ok", version: "1" });
    render(<App />);
    expect(await screen.findByText("Everything is ready.")).toBeDefined();
  });

  it("explains the outage when the database is down", async () => {
    respondWith(503, { status: "unavailable", version: "1" });
    render(<App />);
    expect(await screen.findByText(/not available right now/)).toBeDefined();
  });

  it("explains the outage when the api cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("network"));
    render(<App />);
    expect(await screen.findByText(/not available right now/)).toBeDefined();
  });
});
