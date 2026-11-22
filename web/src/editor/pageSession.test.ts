import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, type Page, UnreachableError } from "../api/client";
import type { Draft, DraftStore } from "./drafts";
import { IDLE_MS, type PageBackend, PageSession, RETRY_MS } from "./pageSession";

function page(version: number, content: string, title = "Title"): Page {
  return { id: "p", version, title, content, saved_at: "", restored_from: null };
}

class MemoryDrafts implements DraftStore {
  readonly drafts = new Map<string, Draft>();
  read = (id: string) => this.drafts.get(id) ?? null;
  write = (id: string, draft: Draft) => void this.drafts.set(id, draft);
  remove = (id: string) => void this.drafts.delete(id);
}

const save = vi.fn<PageBackend["save"]>();
const restoreVersion = vi.fn<PageBackend["restoreVersion"]>();
const onSaved = vi.fn();
let drafts: MemoryDrafts;

function open(opened = page(1, "old")): PageSession {
  return new PageSession(opened, { save, restoreVersion }, drafts, onSaved);
}

describe("PageSession", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
    drafts = new MemoryDrafts();
    save.mockImplementation(async (_id, body) =>
      page(body.base_version + 1, body.content, body.title),
    );
  });
  afterEach(() => vi.useRealTimers());

  it("does not save a page that was only opened", async () => {
    open();
    await vi.advanceTimersByTimeAsync(IDLE_MS * 2);
    expect(save).not.toHaveBeenCalled();
  });

  it("saves once after the user pauses", async () => {
    const session = open();
    session.edit({ content: "n" });
    await vi.advanceTimersByTimeAsync(IDLE_MS - 1);
    session.edit({ content: "new" });
    await vi.advanceTimersByTimeAsync(IDLE_MS);

    expect(save).toHaveBeenCalledExactlyOnceWith("p", {
      title: "Title",
      content: "new",
      base_version: 1,
    });
    expect(session.getState()).toMatchObject({ status: "saved", version: 2 });
  });

  it("keeps a draft until the text is saved", async () => {
    const session = open();
    session.edit({ content: "new" });
    expect(drafts.read("p")).toEqual({ title: "Title", content: "new", base: 1 });
    await session.flush();
    expect(drafts.read("p")).toBeNull();
  });

  it("brings back an unsaved draft and saves it against its own base", async () => {
    drafts.write("p", { title: "Title", content: "draft", base: 1 });
    const session = open(page(3, "newer"));
    expect(session.getState()).toMatchObject({ content: "draft", draftRestored: true });
    await session.flush();
    expect(save.mock.calls[0]?.[1].base_version).toBe(1);
  });

  it("saves again what was typed during a save", async () => {
    const session = open();
    session.edit({ content: "a" });
    const first = session.flush();
    session.edit({ content: "ab" });
    await first;
    expect(session.getState().status).toBe("dirty");
    await vi.advanceTimersByTimeAsync(IDLE_MS);
    expect(save.mock.calls.map(([, body]) => [body.content, body.base_version])).toEqual([
      ["a", 1],
      ["ab", 2],
    ]);
  });

  it("keeps the text while offline and retries", async () => {
    save.mockRejectedValueOnce(new UnreachableError());
    const session = open();
    session.edit({ content: "new" });
    await session.flush();
    expect(session.getState().status).toBe("offline");
    expect(drafts.read("p")?.content).toBe("new");
    await vi.advanceTimersByTimeAsync(RETRY_MS);
    expect(session.getState().status).toBe("saved");
  });

  it("stops and asks when the page was changed elsewhere", async () => {
    save.mockRejectedValueOnce(new ApiError(409, "version_conflict", "", page(2, "theirs")));
    const session = open();
    session.edit({ content: "mine" });
    await session.flush();
    expect(session.getState()).toMatchObject({ status: "conflict", content: "mine" });

    session.edit({ content: "mine!" });
    await vi.advanceTimersByTimeAsync(IDLE_MS * 2);
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("can continue with the user's text", async () => {
    save.mockRejectedValueOnce(new ApiError(409, "version_conflict", "", page(2, "theirs")));
    const session = open();
    session.edit({ content: "mine" });
    await session.flush();
    await session.keepMine();
    expect(save.mock.lastCall?.[1]).toMatchObject({ content: "mine", base_version: 2 });
    expect(session.getState()).toMatchObject({ status: "saved", version: 3, conflict: null });
  });

  it("can continue with the other text without losing the user's", async () => {
    save.mockRejectedValueOnce(new ApiError(409, "version_conflict", "", page(2, "theirs")));
    restoreVersion.mockResolvedValue(page(4, "theirs"));
    const session = open();
    session.edit({ content: "mine" });
    await session.flush();
    await session.keepTheirs();
    expect(save.mock.lastCall?.[1]).toMatchObject({ content: "mine", base_version: 2 });
    expect(restoreVersion).toHaveBeenCalledWith("p", 2);
    expect(session.getState()).toMatchObject({ content: "theirs", version: 4, revision: 1 });
  });

  it("shows why a save was rejected", async () => {
    save.mockRejectedValueOnce(new ApiError(422, "invalid_value", "Too long."));
    const session = open();
    session.edit({ title: "x" });
    await session.flush();
    expect(session.getState()).toMatchObject({ status: "rejected", problem: "Too long." });
  });

  it("gives an empty title a name", async () => {
    const session = open();
    session.edit({ title: "  " });
    await session.flush();
    expect(save.mock.lastCall?.[1].title).toBe("Untitled page");
  });

  it("saves edits that arrive while the page is being closed", async () => {
    const session = open();
    session.dispose();
    session.edit({ content: "last words" });
    await session.flush();
    expect(save.mock.lastCall?.[1].content).toBe("last words");
  });
});
