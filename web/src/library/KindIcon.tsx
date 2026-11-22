import { Bookmark, FileText, Folder, NotebookText } from "lucide-react";
import type { Kind } from "../api/client";

const ICONS = { folder: Folder, notebook: NotebookText, section: Bookmark, page: FileText };

export function KindIcon({ kind }: { kind: Kind }) {
  const Icon = ICONS[kind];
  return <Icon size={16} className={`kind-icon kind-${kind}`} aria-hidden="true" />;
}
