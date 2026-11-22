import { type KeyboardEvent, type ReactNode, useEffect, useId, useRef, useState } from "react";

export type MenuItem = {
  label: string;
  icon: ReactNode;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
};

type Props = { label: string; trigger: ReactNode; className?: string; items: MenuItem[] };

export function Menu({ label, trigger, className = "icon-button", items }: Props) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }
    root.current?.querySelector<HTMLElement>("[role=menuitem]:not(:disabled)")?.focus();
    const closeOutside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  const close = () => {
    setOpen(false);
    root.current?.querySelector("button")?.focus();
  };

  const navigate = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
      return;
    }
    const step = { ArrowDown: 1, ArrowUp: -1 }[event.key];
    if (!step) {
      return;
    }
    event.preventDefault();
    const options = [
      ...(root.current?.querySelectorAll<HTMLElement>("[role=menuitem]:not(:disabled)") ?? []),
    ];
    const index = options.indexOf(document.activeElement as HTMLElement);
    options.at((index + step) % options.length)?.focus();
  };

  return (
    <div className="menu" ref={root}>
      <button
        type="button"
        className={className}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen(!open)}
      >
        {trigger}
      </button>
      {open && (
        <div id={menuId} className="menu-items" role="menu" tabIndex={-1} onKeyDown={navigate}>
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={item.danger ? "menu-item danger" : "menu-item"}
              disabled={item.disabled}
              onClick={() => {
                close();
                item.onSelect();
              }}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
