import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useContext, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { api, type Item, type Kind } from "../api/client";
import { errorText, useToast } from "../ui/toast";
import { DestinationDialog } from "./DestinationDialog";
import { NameDialog } from "./NameDialog";
import { Library } from "./tree";

type LibraryActions = {
  library: Library;
  create: (kind: Kind, parentId: string | null) => void;
  rename: (item: Item) => void;
  chooseDestination: (item: Item) => void;
  moveInto: (itemId: string, parentId: string | null) => void;
  shift: (item: Item, step: -1 | 1) => void;
  trash: (item: Item) => void;
};

type OpenDialog =
  | { type: "create"; kind: Kind; parentId: string | null }
  | { type: "rename"; item: Item }
  | { type: "move"; item: Item }
  | null;

const LibraryContext = createContext<LibraryActions | null>(null);
/** Larger than any list, so that the api appends at the end. */
const AT_END = 1_000_000;

export function useLibrary(): LibraryActions {
  const value = useContext(LibraryContext);
  if (!value) {
    throw new Error("useLibrary needs a LibraryProvider");
  }
  return value;
}

export function LibraryProvider({ children }: { children: ReactNode }) {
  const queries = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [dialog, setDialog] = useState<OpenDialog>(null);
  const { data: items = [] } = useQuery({ queryKey: ["items"], queryFn: api.items });
  const library = useMemo(() => new Library(items), [items]);

  const change = useMutation({
    mutationFn: (work: () => Promise<unknown>) => work(),
    onError: (error) => toast(errorText(error)),
    onSettled: () =>
      Promise.all([
        queries.invalidateQueries({ queryKey: ["items"] }),
        queries.invalidateQueries({ queryKey: ["trash"] }),
      ]),
  });

  const open = (item: Item) => {
    if (item.kind === "page") {
      navigate(`/page/${item.id}`);
    } else if (item.kind === "section") {
      navigate(`/section/${item.id}`);
    }
  };

  const createItem = (kind: Kind, parentId: string | null, title: string) =>
    change.mutate(async () => {
      const created = await api.create(kind, title, parentId);
      await queries.invalidateQueries({ queryKey: ["items"] });
      open(created);
    });

  const actions: LibraryActions = {
    library,
    create: (kind, parentId) => setDialog({ type: "create", kind, parentId }),
    rename: (item) => setDialog({ type: "rename", item }),
    chooseDestination: (item) => setDialog({ type: "move", item }),
    moveInto: (itemId, parentId) => {
      const item = library.get(itemId);
      if (item && item.parent_id !== parentId && library.canPlace(item, parentId)) {
        change.mutate(() => api.move(itemId, parentId, AT_END));
      }
    },
    shift: (item, step) => {
      const index = library.children(item.parent_id).findIndex(({ id }) => id === item.id);
      change.mutate(() => api.move(item.id, item.parent_id, Math.max(0, index + step)));
    },
    trash: (item) => change.mutate(() => api.trash(item.id)),
  };

  const close = () => setDialog(null);

  return (
    <LibraryContext value={actions}>
      {children}
      {dialog?.type === "create" && (
        <NameDialog
          kind={dialog.kind}
          onClose={close}
          onSubmit={(title) => createItem(dialog.kind, dialog.parentId, title)}
        />
      )}
      {dialog?.type === "rename" && (
        <NameDialog
          kind={dialog.item.kind}
          initial={dialog.item.title}
          onClose={close}
          onSubmit={(title) => change.mutate(() => api.rename(dialog.item.id, title))}
        />
      )}
      {dialog?.type === "move" && (
        <DestinationDialog
          item={dialog.item}
          library={library}
          onClose={close}
          onChoose={(parentId) => change.mutate(() => api.move(dialog.item.id, parentId, AT_END))}
        />
      )}
    </LibraryContext>
  );
}
