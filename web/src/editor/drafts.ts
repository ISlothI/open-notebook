export type Draft = { title: string; content: string; base: number };

export type DraftStore = {
  read(pageId: string): Draft | null;
  write(pageId: string, draft: Draft): void;
  remove(pageId: string): void;
};

const PREFIX = "open-notebook:draft:";

/** Drafts are a safety net: a full or blocked storage must never break editing. */
export const localDrafts: DraftStore = {
  read(pageId) {
    try {
      const stored = localStorage.getItem(PREFIX + pageId);
      return stored ? (JSON.parse(stored) as Draft) : null;
    } catch {
      return null;
    }
  },
  write(pageId, draft) {
    try {
      localStorage.setItem(PREFIX + pageId, JSON.stringify(draft));
    } catch {
      // The text is still in the editor and will be saved on the server.
    }
  },
  remove(pageId) {
    try {
      localStorage.removeItem(PREFIX + pageId);
    } catch {
      // Nothing to clean up without storage.
    }
  },
};

/** Drafts contain note text, so they must not outlive the session on a shared computer. */
export function removeAllDrafts(): void {
  try {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith(PREFIX)) {
        localStorage.removeItem(key);
      }
    }
  } catch {
    // Nothing to clean up without storage.
  }
}
