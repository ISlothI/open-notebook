import { X } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef } from "react";
import { messages } from "../messages";

type Props = {
  title: string;
  lead?: string;
  wide?: boolean;
  onClose: () => void;
  children: ReactNode;
};

/** A modal dialog; the native element provides focus trapping and Escape. */
export function Dialog({ title, lead, wide = false, onClose, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      className={wide ? "dialog dialog-wide" : "dialog"}
      aria-labelledby={titleId}
      onClose={onClose}
    >
      <header className="dialog-header">
        <div>
          <h2 id={titleId}>{title}</h2>
          {lead && <p className="muted">{lead}</p>}
        </div>
        <button
          type="button"
          className="icon-button"
          aria-label={messages.close}
          onClick={() => dialog.current?.close()}
        >
          <X size={18} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
