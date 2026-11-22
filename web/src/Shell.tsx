import { BookOpen, FileText, PanelLeft, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet, useLocation, useParams } from "react-router";
import type { User } from "./api/client";
import { useLibrary } from "./library/LibraryContext";
import { PageList } from "./library/PageList";
import { Sidebar } from "./library/Sidebar";
import { messages } from "./messages";
import { EmptyState } from "./ui/EmptyState";
import { ErrorBoundary } from "./ui/ErrorBoundary";

const NARROW_SCREEN = "(max-width: 860px)";

export function Shell({ user }: { user: User }) {
  const { library } = useLibrary();
  const { pageId, sectionId } = useParams();
  const { pathname } = useLocation();
  const [columnsOpen, setColumnsOpen] = useState(() => !window.matchMedia(NARROW_SCREEN).matches);
  const section = library.get(sectionId ?? library.get(pageId)?.parent_id);

  useEffect(() => {
    // On a narrow screen the columns cover the page, so choosing one reveals it.
    if (pageId && window.matchMedia(NARROW_SCREEN).matches) {
      setColumnsOpen(false);
    }
  }, [pageId]);

  return (
    <div className={columnsOpen ? "shell" : "shell columns-closed"}>
      <button
        type="button"
        className="icon-button columns-toggle"
        aria-label={columnsOpen ? messages.library.hide : messages.library.show}
        aria-expanded={columnsOpen}
        onClick={() => setColumnsOpen(!columnsOpen)}
      >
        <PanelLeft size={18} />
      </button>
      {columnsOpen && (
        <div className="columns">
          <Sidebar user={user} activeSectionId={section?.id} />
          {section && <PageList section={section} />}
        </div>
      )}
      <main className="content">
        <ErrorBoundary key={pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}

export function Welcome() {
  const { library, create } = useLibrary();
  const isEmpty = library.children(null).length === 0;
  return (
    <EmptyState
      icon={<BookOpen size={36} />}
      title={isEmpty ? messages.library.empty : messages.tagline}
      lead={isEmpty ? messages.library.emptyLead : messages.pages.select}
    >
      {isEmpty && (
        <button type="button" className="button primary" onClick={() => create("notebook", null)}>
          <Plus size={16} aria-hidden="true" />
          {messages.library.newNamed(messages.kinds.notebook)}
        </button>
      )}
    </EmptyState>
  );
}

export function SectionView() {
  const { sectionId = "" } = useParams();
  const { create } = useLibrary();
  return (
    <EmptyState icon={<FileText size={36} />} title={messages.pages.select}>
      <button type="button" className="button primary" onClick={() => create("page", sectionId)}>
        <Plus size={16} aria-hidden="true" />
        {messages.library.newNamed(messages.kinds.page)}
      </button>
    </EmptyState>
  );
}
