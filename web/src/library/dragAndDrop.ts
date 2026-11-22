import { type DragEvent, useState } from "react";
import { useLibrary } from "./LibraryContext";

const ITEM_TYPE = "application/x-open-notebook-item";

export function dragSource(itemId: string) {
  return {
    draggable: true,
    onDragStart: (event: DragEvent) => {
      event.dataTransfer.setData(ITEM_TYPE, itemId);
      event.dataTransfer.effectAllowed = "move";
    },
  };
}

/** Mouse shortcut for "Move to…", which is the keyboard-accessible way. */
export function useDropTarget(parentId: string | null) {
  const { moveInto } = useLibrary();
  const [isOver, setIsOver] = useState(false);
  return {
    isOver,
    handlers: {
      onDragOver: (event: DragEvent) => {
        if (event.dataTransfer.types.includes(ITEM_TYPE)) {
          event.preventDefault();
          event.stopPropagation();
          setIsOver(true);
        }
      },
      onDragLeave: () => setIsOver(false),
      onDrop: (event: DragEvent) => {
        event.preventDefault();
        event.stopPropagation();
        setIsOver(false);
        moveInto(event.dataTransfer.getData(ITEM_TYPE), parentId);
      },
    },
  };
}
