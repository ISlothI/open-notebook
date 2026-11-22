import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { api, type SearchHit } from "../api/client";
import { useLibrary } from "../library/LibraryContext";
import { messages } from "../messages";
import { errorText } from "../ui/toast";
import { useDebounced } from "./useDebounced";

const TYPING_PAUSE_MS = 200;
const text = messages.search;

export function SearchDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();
  const { library } = useLibrary();
  const [input, setInput] = useState("");
  const [notebookId, setNotebookId] = useState<string | null>(null);
  const [selected, setSelected] = useState(0);
  const listId = useId();
  const query = useDebounced(input.trim(), TYPING_PAUSE_MS);

  const { data, error } = useQuery({
    queryKey: ["search", query, notebookId],
    queryFn: ({ signal }) => api.search(query, notebookId, signal),
    enabled: query !== "",
    placeholderData: keepPreviousData,
    staleTime: 0,
  });
  const hits = query === "" ? [] : (data?.hits ?? []);
  const active = Math.min(selected, hits.length - 1);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  const open = (hit: SearchHit) => {
    dialog.current?.close();
    navigate(`/page/${hit.page_id}`);
  };

  const navigateResults = (event: KeyboardEvent) => {
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    const hit = hits[active];
    if (step && hits.length > 0) {
      event.preventDefault();
      const next = (active + step + hits.length) % hits.length;
      setSelected(next);
      document.getElementById(`${listId}-${next}`)?.scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && hit) {
      event.preventDefault();
      open(hit);
    }
  };

  const status = () => {
    if (query === "") {
      return text.hint;
    }
    if (error) {
      return errorText(error);
    }
    return data && hits.length === 0 ? text.nothing : "";
  };

  return (
    <dialog ref={dialog} className="dialog search-dialog" aria-label={text.label} onClose={onClose}>
      <div className="search-bar">
        <Search size={20} aria-hidden="true" />
        <input
          role="combobox"
          aria-label={text.label}
          aria-expanded={hits.length > 0}
          aria-controls={listId}
          aria-activedescendant={hits.length > 0 ? `${listId}-${active}` : undefined}
          placeholder={text.placeholder}
          maxLength={300}
          value={input}
          onChange={(event) => {
            setInput(event.target.value);
            setSelected(0);
          }}
          onKeyDown={navigateResults}
        />
        <select
          aria-label={text.scope}
          value={notebookId ?? ""}
          onChange={(event) => setNotebookId(event.target.value || null)}
        >
          <option value="">{text.everywhere}</option>
          {library.notebooks().map((notebook) => (
            <option key={notebook.id} value={notebook.id}>
              {notebook.title}
            </option>
          ))}
        </select>
      </div>
      {query !== "" && data?.mode === "fulltext" && (
        <p className="search-degraded">{text.degraded}</p>
      )}
      <div className="search-results" id={listId} role="listbox" aria-label={text.results}>
        {hits.map((hit, index) => (
          // biome-ignore lint/a11y/useKeyWithClickEvents: the combobox handles the keyboard
          // biome-ignore lint/a11y/useFocusableInteractive: focus stays in the combobox
          <div
            key={hit.page_id}
            id={`${listId}-${index}`}
            role="option"
            aria-selected={index === active}
            className="search-hit"
            onClick={() => open(hit)}
            onPointerMove={() => setSelected(index)}
          >
            <strong>{hit.title}</strong>
            <small>
              {hit.notebook_title} / {hit.section_title}
            </small>
            <p>
              {hit.snippet.map((part, position) =>
                part.is_match ? (
                  <mark key={`${position}-${part.text}`}>{part.text}</mark>
                ) : (
                  part.text
                ),
              )}
            </p>
          </div>
        ))}
      </div>
      <p className="search-status" role="status">
        {status()}
      </p>
    </dialog>
  );
}
