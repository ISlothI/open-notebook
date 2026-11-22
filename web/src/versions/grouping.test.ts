import { describe, expect, it } from "vitest";
import type { Version } from "../api/client";
import { groupVersions } from "./grouping";

function version(number: number, minute: number, restored_from: number | null = null): Version {
  const saved_at = new Date(Date.UTC(2026, 0, 1, 12, minute)).toISOString();
  return { version: number, title: "t", saved_at, restored_from };
}

const shape = (versions: Version[]) =>
  groupVersions(versions).map(({ head, earlier }) => [
    head.version,
    ...earlier.map((item) => item.version),
  ]);

describe("groupVersions", () => {
  it("joins versions saved within minutes", () => {
    expect(shape([version(4, 45), version(3, 12), version(2, 9), version(1, 5)])).toEqual([
      [4],
      [3, 2, 1],
    ]);
  });

  it("never hides a restored version", () => {
    expect(shape([version(3, 3), version(2, 2, 1), version(1, 1)])).toEqual([[3], [2], [1]]);
  });

  it("accepts an empty history", () => {
    expect(shape([])).toEqual([]);
  });
});
