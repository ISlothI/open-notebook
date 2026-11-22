import { describe, expect, it } from "vitest";
import type { Item, Kind } from "../api/client";
import { Library } from "./tree";

function item(id: string, kind: Kind, parent_id: string | null): Item {
  return { id, kind, parent_id, title: id, position: 0, created_at: "", trashed_at: null };
}

const outer = item("outer", "folder", null);
const inner = item("inner", "folder", "outer");
const notebook = item("notebook", "notebook", "inner");
const section = item("section", "section", "notebook");
const page = item("page", "page", "section");
const library = new Library([outer, inner, notebook, section, page]);

describe("Library", () => {
  it("knows the path of an item", () => {
    expect(library.path("page").map(({ id }) => id)).toEqual([
      "outer",
      "inner",
      "notebook",
      "section",
      "page",
    ]);
  });

  it("refuses to place a folder inside itself", () => {
    expect(library.canPlace(outer, "inner")).toBe(false);
    expect(library.canPlace(outer, "outer")).toBe(false);
  });

  it("follows the hierarchy rules", () => {
    expect(library.canPlace(page, "notebook")).toBe(false);
    expect(library.canPlace(notebook, null)).toBe(true);
    expect(library.canPlace(section, null)).toBe(false);
    expect(library.canPlace(section, "unknown")).toBe(false);
  });

  it("offers only places where the item is not yet", () => {
    expect(library.destinations(notebook).map((target) => target?.id ?? null)).toEqual([
      null,
      "outer",
    ]);
  });

  it("offers the old place for an item that is not in the library", () => {
    const trashed = item("trashed", "section", "notebook");
    expect(library.destinations(trashed).map((target) => target?.id)).toEqual(["notebook"]);
  });
});
