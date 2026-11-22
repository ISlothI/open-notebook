import { useMutation, useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { api, type Version } from "../api/client";
import { messages } from "../messages";
import { errorText, useToast } from "../ui/toast";
import { groupVersions, type VersionGroup } from "./grouping";
import { VersionDialog } from "./VersionDialog";

type Props = {
  pageId: string;
  current: { title: string; content: string; version: number };
  onRestore: (number: number) => Promise<void>;
  onClose: () => void;
};

const text = messages.versions;
const TIME = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

export function VersionPanel({ pageId, current, onRestore, onClose }: Props) {
  const [selected, setSelected] = useState<number | null>(null);
  const toast = useToast();
  const { data: versions = [] } = useQuery({
    queryKey: ["versions", pageId],
    queryFn: () => api.versions(pageId),
  });
  const restoration = useMutation({
    mutationFn: onRestore,
    onSuccess: () => setSelected(null),
    onError: (error) => toast(errorText(error)),
  });

  return (
    <aside className="version-panel" aria-label={text.title}>
      <div className="column-heading">
        <h2>{text.title}</h2>
        <button type="button" className="icon-button" aria-label={messages.close} onClick={onClose}>
          <X size={18} />
        </button>
      </div>
      <ol className="timeline">
        {groupVersions(versions).map((group) => (
          <Group
            key={group.head.version}
            group={group}
            currentNumber={versions[0]?.version}
            onSelect={setSelected}
          />
        ))}
      </ol>
      {selected !== null && (
        <VersionDialog
          pageId={pageId}
          number={selected}
          current={current}
          restoring={restoration.isPending}
          onRestore={() => restoration.mutate(selected)}
          onClose={() => setSelected(null)}
        />
      )}
    </aside>
  );
}

type GroupProps = {
  group: VersionGroup;
  currentNumber: number | undefined;
  onSelect: (number: number) => void;
};

function Group({ group, currentNumber, onSelect }: GroupProps) {
  const [open, setOpen] = useState(false);
  const { head, earlier } = group;

  return (
    <li>
      <Entry version={head} isCurrent={head.version === currentNumber} onSelect={onSelect} />
      {open &&
        earlier.map((version) => (
          <Entry key={version.version} version={version} isCurrent={false} onSelect={onSelect} />
        ))}
      {earlier.length > 0 && (
        <button type="button" className="link-button" onClick={() => setOpen(!open)}>
          {open ? text.fewer : text.earlier(earlier.length)}
        </button>
      )}
    </li>
  );
}

type EntryProps = { version: Version; isCurrent: boolean; onSelect: (number: number) => void };

function Entry({ version, isCurrent, onSelect }: EntryProps) {
  return (
    <button type="button" className="timeline-entry" onClick={() => onSelect(version.version)}>
      <span className="timeline-time">{TIME.format(new Date(version.saved_at))}</span>
      <span className="muted">
        {isCurrent ? text.current : text.version(version.version)}
        {version.restored_from !== null && ` · ${text.restoredFrom(version.restored_from)}`}
      </span>
    </button>
  );
}
