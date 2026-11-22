import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2, Undo2 } from "lucide-react";
import { useState } from "react";
import { ApiError, api, type Item } from "../api/client";
import { DestinationDialog } from "../library/DestinationDialog";
import { KindIcon } from "../library/KindIcon";
import { useLibrary } from "../library/LibraryContext";
import { messages } from "../messages";
import { EmptyState } from "../ui/EmptyState";
import { errorText, useToast } from "../ui/toast";

const text = messages.trash;
const DATE = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

type Restoration = { item: Item; parentId: string | null };

export function TrashView() {
  const queries = useQueryClient();
  const toast = useToast();
  const { library } = useLibrary();
  const [needsPlace, setNeedsPlace] = useState<Item | null>(null);
  const { data: items } = useQuery({ queryKey: ["trash"], queryFn: api.listTrash });

  const restoration = useMutation({
    mutationFn: ({ item, parentId }: Restoration) => api.restore(item.id, parentId),
    onError: (error, { item }) => {
      if (error instanceof ApiError && error.code === "parent_trashed") {
        setNeedsPlace(item);
      } else {
        toast(errorText(error));
      }
    },
    onSettled: () =>
      Promise.all([
        queries.invalidateQueries({ queryKey: ["items"] }),
        queries.invalidateQueries({ queryKey: ["trash"] }),
      ]),
  });

  return (
    <section className="list-view">
      <header>
        <h1>{text.title}</h1>
        <p className="muted">{text.lead}</p>
      </header>
      {items?.length === 0 && (
        <EmptyState icon={<Trash2 size={32} />} title={text.empty} lead={text.emptyLead} />
      )}
      <ul className="row-list">
        {items?.map((item) => (
          <li key={item.id} className="list-row">
            <KindIcon kind={item.kind} />
            <div className="row-name">
              <span>{item.title}</span>
              <small className="muted">
                {messages.kinds[item.kind]}
                {item.trashed_at && ` · ${text.deleted(DATE.format(new Date(item.trashed_at)))}`}
              </small>
            </div>
            <button
              type="button"
              className="button"
              aria-label={`${text.restore} ${item.title}`}
              onClick={() => restoration.mutate({ item, parentId: null })}
            >
              <Undo2 size={16} aria-hidden="true" />
              {text.restore}
            </button>
          </li>
        ))}
      </ul>
      {needsPlace && (
        <DestinationDialog
          item={needsPlace}
          library={library}
          title={text.chooseTitle(needsPlace.title)}
          lead={text.chooseLead}
          onClose={() => setNeedsPlace(null)}
          onChoose={(parentId) => restoration.mutate({ item: needsPlace, parentId })}
        />
      )}
    </section>
  );
}
