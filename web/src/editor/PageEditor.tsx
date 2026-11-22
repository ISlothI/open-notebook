import { useQueryClient } from "@tanstack/react-query";
import { Code, History } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api, type Page } from "../api/client";
import { useLibrary } from "../library/LibraryContext";
import { messages } from "../messages";
import { VersionPanel } from "../versions/VersionPanel";
import { ConflictDialog } from "./ConflictDialog";
import { localDrafts } from "./drafts";
import { PageSession, type PageState } from "./pageSession";

// The editor is by far the largest part of the application, so it is loaded on demand.
const RichTextEditor = lazy(() =>
  import("./RichTextEditor").then((module) => ({ default: module.RichTextEditor })),
);

const text = messages.pages;

function usePageSession(page: Page): [PageSession, PageState] {
  const queries = useQueryClient();
  const [session] = useState(
    () =>
      new PageSession(
        page,
        { save: api.savePage, restoreVersion: api.restoreVersion },
        localDrafts,
        (saved) => {
          void queries.invalidateQueries({ queryKey: ["versions", saved.id] });
          void queries.invalidateQueries({ queryKey: ["items"] });
        },
      ),
  );

  useEffect(() => {
    const saveWhenHidden = () => {
      if (document.visibilityState === "hidden") {
        void session.flush();
      }
    };
    document.addEventListener("visibilitychange", saveWhenHidden);
    session.resume();
    return () => {
      document.removeEventListener("visibilitychange", saveWhenHidden);
      session.dispose();
    };
  }, [session]);

  return [session, useSyncExternalStore(session.subscribe, session.getState)];
}

export function PageEditor({ page }: { page: Page }) {
  const { library } = useLibrary();
  const [session, state] = usePageSession(page);
  const [showSource, setShowSource] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const historyButton = useRef<HTMLButtonElement>(null);
  const breadcrumb = library
    .path(library.get(page.id)?.parent_id)
    .map((item) => item.title)
    .join(" / ");

  useEffect(() => {
    const saveNow = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "s") {
        event.preventDefault();
        void session.flush();
      }
    };
    document.addEventListener("keydown", saveNow);
    return () => document.removeEventListener("keydown", saveNow);
  }, [session]);

  return (
    <div className="page-view">
      <div className="page-main">
        <div className="page-toolbar">
          <p className="breadcrumb">{breadcrumb}</p>
          <span className={`save-status status-${state.status}`} role="status">
            {state.problem ?? text[state.status]}
          </span>
          <button
            type="button"
            className="icon-button"
            aria-label={showSource ? text.richText : text.source}
            aria-pressed={showSource}
            onClick={() => setShowSource(!showSource)}
          >
            <Code size={18} />
          </button>
          <button
            ref={historyButton}
            type="button"
            className="icon-button"
            aria-label={text.history}
            aria-pressed={showHistory}
            onClick={() => setShowHistory(!showHistory)}
          >
            <History size={18} />
          </button>
        </div>
        <div className="page-scroll">
          <article className="sheet">
            <h1 className="visually-hidden">{state.title}</h1>
            {state.draftRestored && <p className="notice">{text.draftRestored}</p>}
            <textarea
              className="page-title"
              aria-label={text.titleLabel}
              rows={1}
              maxLength={200}
              value={state.title}
              onChange={(event) => session.edit({ title: event.target.value.replace(/\n/g, " ") })}
            />
            {showSource ? (
              <textarea
                className="source-text"
                aria-label={text.contentLabel}
                spellCheck={false}
                value={state.content}
                onChange={(event) => session.edit({ content: event.target.value })}
              />
            ) : (
              <Suspense fallback={<p className="muted">{messages.loading}</p>}>
                <RichTextEditor
                  key={state.revision}
                  initial={state.content}
                  onChange={(content) => session.edit({ content })}
                />
              </Suspense>
            )}
          </article>
        </div>
      </div>
      {showHistory && (
        <VersionPanel
          pageId={page.id}
          current={state}
          onClose={() => {
            setShowHistory(false);
            historyButton.current?.focus();
          }}
          onRestore={async (number) => {
            await session.flush();
            session.replace(await api.restoreVersion(page.id, number));
          }}
        />
      )}
      {state.conflict && (
        <ConflictDialog
          mine={state.content}
          theirs={state.conflict.content}
          onKeepMine={() => session.keepMine()}
          onKeepTheirs={() => session.keepTheirs()}
        />
      )}
    </div>
  );
}
