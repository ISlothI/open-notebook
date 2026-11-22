import type { ReactNode } from "react";

type Props = { icon: ReactNode; title: string; lead?: string; children?: ReactNode };

export function EmptyState({ icon, title, lead, children }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h1>{title}</h1>
      {lead && <p className="muted">{lead}</p>}
      {children}
    </div>
  );
}
