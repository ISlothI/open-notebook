import { ApiError, type Page, type SaveRequest } from "../api/client";
import { messages } from "../messages";
import type { DraftStore } from "./drafts";

export type SaveStatus = "saved" | "dirty" | "saving" | "offline" | "rejected" | "conflict";

export type PageState = {
  readonly title: string;
  readonly content: string;
  readonly status: SaveStatus;
  readonly version: number;
  readonly problem: string | null;
  /** The text that somebody else saved, while the user has to decide. */
  readonly conflict: Page | null;
  /** Changes when the text is replaced from outside the editor. */
  readonly revision: number;
  readonly draftRestored: boolean;
};

export type PageBackend = {
  save(pageId: string, request: SaveRequest): Promise<Page>;
  restoreVersion(pageId: string, version: number): Promise<Page>;
};

export const IDLE_MS = 4_000;
export const RETRY_MS = 10_000;

/**
 * Keeps one open page safe: every edit is stored on the device at once and saved on the server
 * when the user pauses. A conflicting save never overwrites anything by itself.
 */
export class PageSession {
  private state: PageState;
  private readonly listeners = new Set<() => void>();
  private timer: ReturnType<typeof setTimeout> | undefined;
  private running: Promise<void> | null = null;
  private disposed = false;

  constructor(
    private readonly page: Page,
    private readonly backend: PageBackend,
    private readonly drafts: DraftStore,
    private readonly onSaved: (page: Page) => void,
  ) {
    const draft = drafts.read(page.id);
    const isNewer = draft && (draft.title !== page.title || draft.content !== page.content);
    this.state = {
      title: isNewer ? draft.title : page.title,
      content: isNewer ? draft.content : page.content,
      status: isNewer ? "dirty" : "saved",
      version: isNewer ? draft.base : page.version,
      problem: null,
      conflict: null,
      revision: 0,
      draftRestored: Boolean(isNewer),
    };
    if (isNewer) {
      this.schedule(IDLE_MS);
    } else {
      drafts.remove(page.id);
    }
  }

  readonly getState = (): PageState => this.state;

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  edit(change: { title?: string; content?: string }): void {
    const title = change.title ?? this.state.title;
    const content = change.content ?? this.state.content;
    if (title === this.state.title && content === this.state.content) {
      return;
    }
    const inConflict = this.state.status === "conflict";
    this.update({ title, content, problem: null, status: inConflict ? "conflict" : "dirty" });
    this.storeDraft();
    if (this.disposed) {
      void this.flush();
    } else if (!inConflict) {
      this.schedule(IDLE_MS);
    }
  }

  /** Saves pending edits now; concurrent calls share the running save. */
  async flush(): Promise<void> {
    clearTimeout(this.timer);
    if (this.running) {
      await this.running;
    }
    if (this.state.status === "dirty" || this.state.status === "offline") {
      this.running = this.saveOnce(this.state.version).finally(() => {
        this.running = null;
      });
      await this.running;
    }
  }

  async keepMine(): Promise<void> {
    const { conflict } = this.state;
    if (conflict) {
      await this.saveOnce(conflict.version);
    }
  }

  /** Saves the user's text as a version as well, so that choosing the other one loses nothing. */
  async keepTheirs(): Promise<void> {
    const { conflict } = this.state;
    if (!conflict) {
      return;
    }
    await this.saveOnce(conflict.version);
    if (this.getState().status !== "saved") {
      return;
    }
    const restored = await this.backend.restoreVersion(this.page.id, conflict.version);
    this.replace(restored);
  }

  /** Continues with a text that came from the server, such as a restored version. */
  replace(page: Page): void {
    clearTimeout(this.timer);
    this.drafts.remove(this.page.id);
    this.update({
      title: page.title,
      content: page.content,
      version: page.version,
      status: "saved",
      problem: null,
      conflict: null,
      revision: this.state.revision + 1,
    });
    this.onSaved(page);
  }

  /** Undoes `dispose`, which React calls once more than expected in its strict mode. */
  resume(): void {
    this.disposed = false;
  }

  dispose(): void {
    this.disposed = true;
    void this.flush();
  }

  private async saveOnce(base: number): Promise<void> {
    const { title, content } = this.state;
    this.update({ status: "saving", problem: null });
    try {
      const saved = await this.backend.save(this.page.id, {
        title: title.trim() || messages.pages.untitled,
        content,
        base_version: base,
      });
      this.finishSave(saved, title, content);
    } catch (error) {
      this.handleFailure(error);
    }
  }

  private finishSave(saved: Page, title: string, content: string): void {
    const unchanged = this.state.title === title && this.state.content === content;
    this.update({
      version: saved.version,
      conflict: null,
      status: unchanged ? "saved" : "dirty",
      draftRestored: false,
    });
    if (unchanged) {
      this.drafts.remove(this.page.id);
    } else {
      this.storeDraft();
      this.schedule(IDLE_MS);
    }
    this.onSaved(saved);
  }

  private handleFailure(error: unknown): void {
    if (error instanceof ApiError && error.current) {
      this.update({ status: "conflict", conflict: error.current });
    } else if (error instanceof ApiError) {
      this.update({ status: "rejected", problem: error.message });
    } else {
      this.update({ status: "offline" });
      this.schedule(RETRY_MS);
    }
  }

  private schedule(delay: number): void {
    clearTimeout(this.timer);
    if (!this.disposed) {
      this.timer = setTimeout(() => void this.flush(), delay);
    }
  }

  private storeDraft(): void {
    const { title, content, version } = this.state;
    this.drafts.write(this.page.id, { title, content, base: version });
  }

  private update(change: Partial<PageState>): void {
    this.state = { ...this.state, ...change };
    for (const listener of this.listeners) {
      listener();
    }
  }
}
