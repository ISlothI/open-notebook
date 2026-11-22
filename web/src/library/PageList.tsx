import { Plus } from "lucide-react";
import { NavLink } from "react-router";
import type { Item } from "../api/client";
import { messages } from "../messages";
import { dragSource } from "./dragAndDrop";
import { ItemMenu } from "./ItemMenu";
import { useLibrary } from "./LibraryContext";

export function PageList({ section }: { section: Item }) {
  const { library, create } = useLibrary();
  const pages = library.children(section.id);
  const notebook = library.get(section.parent_id);

  return (
    <section className="page-list" aria-label={section.title}>
      <div className="column-heading">
        <div>
          <p className="eyebrow">{notebook?.title}</p>
          <h2>{section.title}</h2>
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label={messages.library.newNamed(messages.kinds.page)}
          onClick={() => create("page", section.id)}
        >
          <Plus size={18} />
        </button>
      </div>
      {pages.length === 0 && (
        <div className="list-empty">
          <p>{messages.pages.none}</p>
          <p className="muted">{messages.pages.noneLead}</p>
        </div>
      )}
      <ul>
        {pages.map((page) => (
          <li key={page.id} className="page-row" {...dragSource(page.id)}>
            <NavLink to={`/page/${page.id}`} className="page-link">
              {page.title}
            </NavLink>
            <ItemMenu item={page} />
          </li>
        ))}
      </ul>
    </section>
  );
}
