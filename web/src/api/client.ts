import createClient from "openapi-fetch";
import { messages } from "../messages";
import type { components, paths } from "./schema";

export type Item = components["schemas"]["NodeBody"];
export type Kind = components["schemas"]["NodeKind"];
export type Page = components["schemas"]["PageBody"];
export type Version = components["schemas"]["VersionBody"];
export type SearchResults = components["schemas"]["SearchBody"];
export type SearchHit = components["schemas"]["SearchHitBody"];
export type User = components["schemas"]["UserBody"];

/** An answer of the api that tells what was wrong. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly current?: Page,
  ) {
    super(message);
  }
}

/** No usable answer arrived: the network or the service is down. */
export class UnreachableError extends Error {
  constructor() {
    super(messages.errors.network);
  }
}

const http = createClient<paths>({ baseUrl: "", fetch: (request) => globalThis.fetch(request) });

type Result<T> = { data?: T; error?: unknown; response: Response };

function toApiError(error: unknown, status: number): ApiError {
  const body = error as { code?: string; message?: string; current?: Page } | undefined;
  return new ApiError(
    status,
    body?.code ?? "unexpected",
    body?.message ?? messages.errors.unexpected,
    body?.current,
  );
}

async function call<T>(request: Promise<Result<T>>): Promise<T> {
  let result: Result<T>;
  try {
    result = await request;
  } catch {
    throw new UnreachableError();
  }
  if (result.response.ok) {
    return result.data as T;
  }
  if (result.response.status >= 500) {
    throw new UnreachableError();
  }
  throw toApiError(result.error, result.response.status);
}

const item = (item_id: string) => ({ params: { path: { item_id } } });
const page = (page_id: string) => ({ params: { path: { page_id } } });
const version = (page_id: string, number: number) => ({ params: { path: { page_id, number } } });

export type Credentials = { email: string; password: string };
export type SaveRequest = { title: string; content: string; base_version: number };

export const api = {
  me: () => call(http.GET("/api/auth/me")),
  register: (body: Credentials) => call(http.POST("/api/auth/register", { body })),
  signIn: (body: Credentials) => call(http.POST("/api/auth/sign-in", { body })),
  signOut: () => call(http.POST("/api/auth/sign-out")),

  items: () => call(http.GET("/api/items")),
  create: (kind: Kind, title: string, parent_id: string | null) =>
    call(http.POST("/api/items", { body: { kind, title, parent_id } })),
  rename: (id: string, title: string) =>
    call(http.PATCH("/api/items/{item_id}", { ...item(id), body: { title } })),
  move: (id: string, parent_id: string | null, position: number) =>
    call(http.POST("/api/items/{item_id}/move", { ...item(id), body: { parent_id, position } })),
  trash: (id: string) => call(http.DELETE("/api/items/{item_id}", item(id))),
  listTrash: () => call(http.GET("/api/trash")),
  restore: (id: string, parent_id: string | null) =>
    call(http.POST("/api/trash/{item_id}/restore", { ...item(id), body: { parent_id } })),

  page: (id: string) => call(http.GET("/api/pages/{page_id}", page(id))),
  savePage: (id: string, body: SaveRequest) =>
    call(http.PUT("/api/pages/{page_id}", { ...page(id), body })),
  versions: (id: string) => call(http.GET("/api/pages/{page_id}/versions", page(id))),
  version: (id: string, number: number) =>
    call(http.GET("/api/pages/{page_id}/versions/{number}", version(id, number))),
  search: (q: string, notebook_id: string | null, signal: AbortSignal) =>
    call(http.GET("/api/search", { params: { query: { q, notebook_id } }, signal })),
  restoreVersion: (id: string, number: number) =>
    call(http.POST("/api/pages/{page_id}/versions/{number}/restore", version(id, number))),
};
