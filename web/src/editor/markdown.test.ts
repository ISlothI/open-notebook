import { defaultValueCtx, Editor, rootCtx } from "@milkdown/kit/core";
import { commonmark } from "@milkdown/kit/preset/commonmark";
import { gfm } from "@milkdown/kit/preset/gfm";
import { getMarkdown } from "@milkdown/kit/utils";
import { describe, expect, it } from "vitest";

async function roundTrip(markdown: string): Promise<string> {
  const root = document.createElement("div");
  const editor = await Editor.make()
    .config((context) => {
      context.set(rootCtx, root);
      context.set(defaultValueCtx, markdown);
    })
    .use(commonmark)
    .use(gfm)
    .create();
  const result = editor.action(getMarkdown());
  await editor.destroy();
  return result;
}

const UNCHANGED = [
  "# A\n\n## B\n\ntext **bold** *italic* ~~gone~~ `code`\n",
  "* a\n* b\n  * c\n\n1. x\n2. y\n",
  "* [ ] todo\n* [x] done\n",
  "| a | b |\n| - | - |\n| 1 | 2 |\n",
  "```python\nprint('x')\n```\n",
  "> quote\n> more\n",
  "[text](https://example.test)\n",
  "line one\nline two\n",
  "a <b>x</b> c\n",
  'Árvíztűrő tükörfúrógép – „idézet"\n',
];

const NORMALISED = ["- a\n- b\n", "a\n\n---\n\nb\n", "a * b _ c\n", "a\n\n\n\nb\n"];

describe("Markdown fidelity of the rich text editor", () => {
  it.each(UNCHANGED)("keeps %j", async (markdown) => {
    expect(await roundTrip(markdown)).toBe(markdown);
  });

  it.each(NORMALISED)("changes the notation of %j only once", async (markdown) => {
    const once = await roundTrip(markdown);
    expect(await roundTrip(once)).toBe(once);
  });
});
