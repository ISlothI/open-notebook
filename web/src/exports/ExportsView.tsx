import { useQuery } from "@tanstack/react-query";
import { Download, FileDown } from "lucide-react";
import { api, type Export } from "../api/client";
import { messages } from "../messages";
import { EmptyState } from "../ui/EmptyState";

const POLL_MS = 1_000;
const DATE = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });
const text = messages.exports;

const isUnfinished = (item: Export) => item.state === "queued" || item.state === "running";

export function ExportsView() {
  const { data: items } = useQuery({
    queryKey: ["exports"],
    queryFn: api.exports,
    refetchInterval: ({ state }) => (state.data?.some(isUnfinished) ? POLL_MS : false),
  });

  return (
    <section className="list-view">
      <header>
        <h1>{text.title}</h1>
        <p className="muted">{text.lead}</p>
      </header>
      {items?.length === 0 && (
        <EmptyState icon={<FileDown size={32} />} title={text.empty} lead={text.emptyLead} />
      )}
      <ul className="row-list">
        {items?.map((item) => (
          <ExportRow key={item.id} item={item} />
        ))}
      </ul>
    </section>
  );
}

function ExportRow({ item }: { item: Export }) {
  return (
    <li className="list-row">
      <FileDown size={18} className="kind-icon" aria-hidden="true" />
      <div className="row-name">
        <span>{item.title}</span>
        <small className="muted">
          {text.states[item.state]} · {DATE.format(new Date(item.created_at))}
        </small>
        {isUnfinished(item) && (
          <progress aria-label={text.progress(item.title)} max={100} value={item.progress} />
        )}
      </div>
      {item.download_url && (
        <a
          className="button"
          href={item.download_url}
          download
          aria-label={`${text.download} ${item.title}`}
        >
          <Download size={16} aria-hidden="true" />
          {text.download}
        </a>
      )}
    </li>
  );
}
