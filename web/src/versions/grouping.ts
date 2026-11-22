import type { Version } from "../api/client";

export const GROUP_WINDOW_MS = 10 * 60_000;

export type VersionGroup = { head: Version; earlier: Version[] };

/**
 * Autosave creates many versions within minutes; the timeline shows the last one of each burst.
 * Restored versions always start a group, because they mark a decision.
 */
export function groupVersions(versions: readonly Version[]): VersionGroup[] {
  const groups: VersionGroup[] = [];
  for (const version of versions) {
    const group = groups.at(-1);
    const isNear =
      group && Date.parse(group.head.saved_at) - Date.parse(version.saved_at) < GROUP_WINDOW_MS;
    if (group && isNear && version.restored_from === null && group.head.restored_from === null) {
      group.earlier.push(version);
    } else {
      groups.push({ head: version, earlier: [] });
    }
  }
  return groups;
}
