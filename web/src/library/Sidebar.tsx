import { useQueryClient } from "@tanstack/react-query";
import { ChevronRight, LogOut, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router";
import { api, type Item, type User } from "../api/client";
import { Logo } from "../brand/Logo";
import { removeAllDrafts } from "../editor/drafts";
import { messages } from "../messages";
import { Menu } from "../ui/Menu";
import { errorText, useToast } from "../ui/toast";
import { dragSource, useDropTarget } from "./dragAndDrop";
import { ItemMenu } from "./ItemMenu";
import { KindIcon } from "./KindIcon";
import { useLibrary } from "./LibraryContext";

const text = messages.library;

export function Sidebar({ user, activeSectionId }: { user: User; activeSectionId?: string }) {
  const { library, create } = useLibrary();
  const drop = useDropTarget(null);
  const rootItems = library.children(null);

  return (
    <nav className="sidebar" aria-label={text.title}>
      <div className="wordmark">
        <Logo />
        <span>{messages.appName}</span>
      </div>
      <div className="column-heading">
        <h2>{text.title}</h2>
        <Menu
          label={text.newItem}
          trigger={<Plus size={18} />}
          items={(["notebook", "folder"] as const).map((kind) => ({
            label: text.newNamed(messages.kinds[kind]),
            icon: <KindIcon kind={kind} />,
            onSelect: () => create(kind, null),
          }))}
        />
      </div>
      <ul className={drop.isOver ? "tree drop-target" : "tree"} {...drop.handlers}>
        {rootItems.map((item) => (
          <TreeNode key={item.id} item={item} activeSectionId={activeSectionId} />
        ))}
      </ul>
      <div className="sidebar-footer">
        <NavLink to="/trash" className="footer-link">
          <Trash2 size={16} aria-hidden="true" />
          {messages.trash.title}
        </NavLink>
        <SignOutButton user={user} />
      </div>
    </nav>
  );
}

function TreeNode({ item, activeSectionId }: { item: Item; activeSectionId?: string }) {
  const { library } = useLibrary();
  const [closed, setClosed] = useState(false);
  const drop = useDropTarget(item.id);
  const isSection = item.kind === "section";
  const children = isSection ? [] : library.children(item.id);

  return (
    <li>
      <div
        className={drop.isOver ? "tree-row drop-target" : "tree-row"}
        {...dragSource(item.id)}
        {...drop.handlers}
      >
        {isSection ? (
          <NavLink
            to={`/section/${item.id}`}
            className={item.id === activeSectionId ? "tree-label active" : "tree-label"}
            aria-current={item.id === activeSectionId ? "true" : undefined}
          >
            <KindIcon kind={item.kind} />
            <span>{item.title}</span>
          </NavLink>
        ) : (
          <button
            type="button"
            className="tree-label"
            aria-expanded={!closed}
            aria-label={closed ? text.expand(item.title) : text.collapse(item.title)}
            onClick={() => setClosed(!closed)}
          >
            <ChevronRight size={14} className={closed ? "chevron" : "chevron open"} />
            <KindIcon kind={item.kind} />
            <span>{item.title}</span>
          </button>
        )}
        <ItemMenu item={item} />
      </div>
      {!closed && children.length > 0 && (
        <ul>
          {children.map((child) => (
            <TreeNode key={child.id} item={child} activeSectionId={activeSectionId} />
          ))}
        </ul>
      )}
    </li>
  );
}

function SignOutButton({ user }: { user: User }) {
  const queries = useQueryClient();
  const toast = useToast();

  const signOut = async () => {
    try {
      await api.signOut();
    } catch (error) {
      toast(errorText(error));
      return;
    }
    removeAllDrafts();
    queries.clear();
    queries.setQueryData(["me"], null);
  };

  return (
    <button type="button" className="footer-link" title={user.email} onClick={signOut}>
      <LogOut size={16} aria-hidden="true" />
      {messages.auth.signOut}
    </button>
  );
}
