import { useEffect, useRef, useState } from "react";
import { messages } from "../messages";

type Props = {
  mine: string;
  theirs: string;
  onKeepMine: () => Promise<void>;
  onKeepTheirs: () => Promise<void>;
};

const text = messages.conflict;

/** Cannot be dismissed, because saving is paused until the user decides. */
export function ConflictDialog({ mine, theirs, onKeepMine, onKeepTheirs }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  const decide = async (decision: () => Promise<void>) => {
    setDeciding(true);
    await decision();
    setDeciding(false);
  };

  return (
    <dialog
      ref={dialog}
      className="dialog dialog-wide"
      aria-labelledby="conflict-title"
      onCancel={(event) => event.preventDefault()}
    >
      <header className="dialog-header">
        <div>
          <h2 id="conflict-title">{text.title}</h2>
          <p className="muted">{text.lead}</p>
        </div>
      </header>
      <div className="compare">
        <section>
          <h3>{text.mine}</h3>
          <pre className="diff">{mine}</pre>
          <button
            type="button"
            className="button primary"
            disabled={deciding}
            onClick={() => decide(onKeepMine)}
          >
            {text.keepMine}
          </button>
        </section>
        <section>
          <h3>{text.theirs}</h3>
          <pre className="diff">{theirs}</pre>
          <button
            type="button"
            className="button"
            disabled={deciding}
            onClick={() => decide(onKeepTheirs)}
          >
            {text.keepTheirs}
          </button>
        </section>
      </div>
    </dialog>
  );
}
