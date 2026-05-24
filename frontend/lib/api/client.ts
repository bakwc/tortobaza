import { getClientRequestLocale } from "@/lib/request-locale-shared";

export type ClientFetchOptions = RequestInit & {
  searchParams?: Record<string, string | number | undefined | null>;
};

function buildPath(path: string, searchParams?: ClientFetchOptions["searchParams"]) {
  const url = new URL(path, "http://placeholder.local");
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return `${url.pathname}${url.search}`;
}

export async function clientFetch<T>(
  path: string,
  { searchParams, headers, body, ...init }: ClientFetchOptions = {},
): Promise<T> {
  const finalHeaders = new Headers(headers);
  finalHeaders.set("Accept", "application/json");
  if (!finalHeaders.has("Accept-Language")) {
    finalHeaders.set("Accept-Language", getClientRequestLocale());
  }
  if (body && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(buildPath(path, searchParams), {
    ...init,
    body,
    headers: finalHeaders,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = "";
    try {
      detail = await response.text();
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }

  parsed<T = unknown>(): T | null {
    try {
      return JSON.parse(this.detail) as T;
    } catch {
      return null;
    }
  }
}
