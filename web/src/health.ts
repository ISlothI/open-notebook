export type Health = { status: "ok" | "unavailable"; version: string };

/** Asks the api whether the whole path down to the database works. */
export async function fetchHealth(signal: AbortSignal): Promise<Health> {
  const response = await fetch("/api/health/ready", { signal });
  if (!response.ok && response.status !== 503) {
    throw new Error(`Unexpected health response: ${response.status}`);
  }
  return (await response.json()) as Health;
}
