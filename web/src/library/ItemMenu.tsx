import { ArrowDown, ArrowUp, Ellipsis, FolderInput, Pencil, Plus, Trash2 } from "lucide-react";
import type { Item } from "../api/client";
import { messages } from "../messages";
import { Menu, type MenuItem } from "../ui/Menu";
import { useLibrary } from "./LibraryContext";
import { CHILD_KINDS } from "./tree";

const ICON = { size: 16, "aria-hidden": true } as const;

export function ItemMenu({ item }: { item: Item }) {
  const actions = useLibrary();
  const siblings = actions.library.children(item.parent_id);
  const index = siblings.findIndex(({ id }) => id === item.id);

  const creation: MenuItem[] = CHILD_KINDS[item.kind].map((kind) => ({
    label: messages.library.newNamed(messages.kinds[kind]),
    icon: <Plus {...ICON} />,
    onSelect: () => actions.create(kind, item.id),
  }));

  const items: MenuItem[] = [
    ...creation,
    {
      label: messages.library.rename,
      icon: <Pencil {...ICON} />,
      onSelect: () => actions.rename(item),
    },
    {
      label: messages.library.moveUp,
      icon: <ArrowUp {...ICON} />,
      disabled: index <= 0,
      onSelect: () => actions.shift(item, -1),
    },
    {
      label: messages.library.moveDown,
      icon: <ArrowDown {...ICON} />,
      disabled: index === siblings.length - 1,
      onSelect: () => actions.shift(item, 1),
    },
    {
      label: messages.library.moveTo,
      icon: <FolderInput {...ICON} />,
      onSelect: () => actions.chooseDestination(item),
    },
    {
      label: messages.library.trash,
      icon: <Trash2 {...ICON} />,
      danger: true,
      onSelect: () => actions.trash(item),
    },
  ];

  return (
    <Menu
      label={messages.library.actionsFor(item.title)}
      trigger={<Ellipsis size={16} />}
      className="icon-button row-action"
      items={items}
    />
  );
}
