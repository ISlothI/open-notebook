import type { Item, Kind } from "../api/client";

/** Mirrors the placement rules of the api; null stands for the top level. */
const ALLOWED_PARENTS: Record<Kind, readonly (Kind | null)[]> = {
  folder: [null, "folder"],
  notebook: [null, "folder"],
  section: ["notebook"],
  page: ["section"],
};

export const CHILD_KINDS: Record<Kind, readonly Kind[]> = {
  folder: ["notebook", "folder"],
  notebook: ["section"],
  section: ["page"],
  page: [],
};

export class Library {
  private readonly byId: Map<string, Item>;
  private readonly byParent = new Map<string | null, Item[]>();

  constructor(items: readonly Item[]) {
    this.byId = new Map(items.map((item) => [item.id, item]));
    for (const item of items) {
      const siblings = this.byParent.get(item.parent_id) ?? [];
      siblings.push(item);
      this.byParent.set(item.parent_id, siblings);
    }
  }

  get(id: string | null | undefined): Item | undefined {
    return id ? this.byId.get(id) : undefined;
  }

  children(id: string | null): Item[] {
    return this.byParent.get(id) ?? [];
  }

  /** From the outermost ancestor to the item itself. */
  path(id: string | null | undefined): Item[] {
    const item = this.get(id);
    return item ? [...this.path(item.parent_id), item] : [];
  }

  isInside(id: string, ancestorId: string): boolean {
    return this.path(id).some((item) => item.id === ancestorId);
  }

  canPlace(item: Item, parentId: string | null): boolean {
    const parent = this.get(parentId);
    if (parentId !== null && !parent) {
      return false;
    }
    const kindAllowed = ALLOWED_PARENTS[item.kind].includes(parent?.kind ?? null);
    return kindAllowed && !(parentId !== null && this.isInside(parentId, item.id));
  }

  /** Where the item could go, excluding where it already is. */
  destinations(item: Item): (Item | null)[] {
    const candidates: (Item | null)[] = [null, ...this.depthFirst(null)];
    return candidates.filter(
      (target) =>
        this.canPlace(item, target?.id ?? null) &&
        !(this.byId.has(item.id) && (target?.id ?? null) === item.parent_id),
    );
  }

  private depthFirst(parentId: string | null): Item[] {
    return this.children(parentId).flatMap((item) => [item, ...this.depthFirst(item.id)]);
  }
}
