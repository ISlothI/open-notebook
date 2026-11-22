import type { Item } from "../api/client";
import { messages } from "../messages";
import { Dialog } from "../ui/Dialog";
import { KindIcon } from "./KindIcon";
import type { Library } from "./tree";

type Props = {
  item: Item;
  library: Library;
  title?: string;
  lead?: string;
  onChoose: (parentId: string | null) => void;
  onClose: () => void;
};

export function DestinationDialog({ item, library, title, lead, onChoose, onClose }: Props) {
  const destinations = library.destinations(item);
  const pathOf = (target: Item) =>
    library
      .path(target.parent_id)
      .map((ancestor) => ancestor.title)
      .join(" / ");

  return (
    <Dialog title={title ?? messages.library.moveTitle(item.title)} lead={lead} onClose={onClose}>
      {destinations.length === 0 && <p className="muted">{messages.library.noDestination}</p>}
      <ul className="destinations">
        {destinations.map((target) => (
          <li key={target?.id ?? "root"}>
            <button
              type="button"
              className="destination"
              onClick={() => {
                onChoose(target?.id ?? null);
                onClose();
              }}
            >
              <KindIcon kind={target?.kind ?? "folder"} />
              <span>{target?.title ?? messages.library.root}</span>
              {target && <small className="muted">{pathOf(target)}</small>}
            </button>
          </li>
        ))}
      </ul>
    </Dialog>
  );
}
