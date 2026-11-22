import type { FormEvent } from "react";
import type { Kind } from "../api/client";
import { messages } from "../messages";
import { Dialog } from "../ui/Dialog";

type Props = {
  kind: Kind;
  initial?: string;
  onSubmit: (title: string) => void;
  onClose: () => void;
};

export function NameDialog({ kind, initial = "", onSubmit, onClose }: Props) {
  const kindName = messages.kinds[kind];

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const title = String(new FormData(event.currentTarget).get("title")).trim();
    if (title) {
      onSubmit(title);
      onClose();
    }
  };

  return (
    <Dialog
      title={initial ? messages.library.rename : messages.library.newNamed(kindName)}
      onClose={onClose}
    >
      <form onSubmit={submit} className="stack">
        <label className="field">
          {messages.library.nameOf(kindName)}
          <input name="title" defaultValue={initial} maxLength={200} required />
        </label>
        <div className="dialog-actions">
          <button type="button" className="button" onClick={onClose}>
            {messages.cancel}
          </button>
          <button type="submit" className="button primary">
            {initial ? messages.save : messages.create}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
