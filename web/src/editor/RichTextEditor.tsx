import { CrepeBuilder } from "@milkdown/crepe/builder";
import { blockEdit } from "@milkdown/crepe/feature/block-edit";
import { cursor } from "@milkdown/crepe/feature/cursor";
import { linkTooltip } from "@milkdown/crepe/feature/link-tooltip";
import { listItem } from "@milkdown/crepe/feature/list-item";
import { placeholder } from "@milkdown/crepe/feature/placeholder";
import { table } from "@milkdown/crepe/feature/table";
import { toolbar } from "@milkdown/crepe/feature/toolbar";
import "@milkdown/crepe/theme/common/prosemirror.css";
import "@milkdown/crepe/theme/common/reset.css";
import "@milkdown/crepe/theme/common/block-edit.css";
import "@milkdown/crepe/theme/common/cursor.css";
import "@milkdown/crepe/theme/common/link-tooltip.css";
import "@milkdown/crepe/theme/common/list-item.css";
import "@milkdown/crepe/theme/common/placeholder.css";
import "@milkdown/crepe/theme/common/toolbar.css";
import "@milkdown/crepe/theme/common/table.css";
import { useEffect, useRef } from "react";
import { messages } from "../messages";

type Props = { initial: string; onChange: (markdown: string) => void };

/** Uncontrolled: remount it with a new key to replace the text. */
export function RichTextEditor({ initial, onChange }: Props) {
  const root = useRef<HTMLDivElement>(null);
  const report = useRef(onChange);
  report.current = onChange;
  const firstText = useRef(initial);

  useEffect(() => {
    const editor = new CrepeBuilder({ root: root.current, defaultValue: firstText.current });
    editor
      .addFeature(cursor)
      .addFeature(listItem)
      .addFeature(linkTooltip)
      .addFeature(table)
      .addFeature(toolbar)
      .addFeature(placeholder, { text: messages.pages.placeholder, mode: "doc" })
      .addFeature(blockEdit);

    // Opening a page normalises its notation, which must not count as an edit.
    let known: string | null = null;
    const publish = (markdown: string) => {
      if (known !== null && markdown !== known) {
        known = markdown;
        firstText.current = markdown;
        report.current(markdown);
      }
    };
    editor.on((listener) => listener.markdownUpdated((_context, markdown) => publish(markdown)));

    const created = editor.create().then(() => {
      known = editor.getMarkdown();
      const content = root.current?.querySelector(".ProseMirror");
      content?.setAttribute("aria-label", messages.pages.contentLabel);
      content?.setAttribute("role", "textbox");
      content?.setAttribute("aria-multiline", "true");
    });

    return () => {
      void created.then(() => {
        // The change listener is debounced, so the last keystrokes are collected here.
        publish(editor.getMarkdown());
        return editor.destroy();
      });
    };
  }, []);

  return <div className="rich-text" ref={root} />;
}
