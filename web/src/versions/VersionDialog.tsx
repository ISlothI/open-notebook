import { useQuery } from "@tanstack/react-query";
import { diffWordsWithSpace } from "diff";
import { useMemo } from "react";
import { api } from "../api/client";
import { messages } from "../messages";
import { Dialog } from "../ui/Dialog";

type Props = {
  pageId: string;
  number: number;
  current: { title: string; content: string };
  restoring: boolean;
  onRestore: () => void;
  onClose: () => void;
};

const text = messages.versions;

export function VersionDialog({ pageId, number, current, restoring, onRestore, onClose }: Props) {
  const { data: version } = useQuery({
    queryKey: ["versions", pageId, number],
    queryFn: () => api.version(pageId, number),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const parts = useMemo(
    () => (version ? diffWordsWithSpace(current.content, version.content) : []),
    [version, current.content],
  );
  const isIdentical = version?.content === current.content && version.title === current.title;

  return (
    <Dialog title={text.version(number)} lead={text.compared} wide onClose={onClose}>
      <h3>{version?.title}</h3>
      {isIdentical ? (
        <p className="muted">{text.identical}</p>
      ) : (
        <pre className="diff">
          {parts.map((part, index) => {
            const Tag = part.added ? "ins" : part.removed ? "del" : "span";
            return <Tag key={index}>{part.value}</Tag>;
          })}
        </pre>
      )}
      <div className="dialog-actions">
        <button type="button" className="button" onClick={onClose}>
          {messages.close}
        </button>
        <button
          type="button"
          className="button primary"
          disabled={!version || isIdentical || restoring}
          onClick={onRestore}
        >
          {text.restore}
        </button>
      </div>
    </Dialog>
  );
}
