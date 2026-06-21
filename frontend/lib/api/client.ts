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

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
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

  const method = (init.method ?? "GET").toUpperCase();
  if (!SAFE_METHODS.has(method) && !finalHeaders.has("X-CSRFToken")) {
    const csrfToken = readCookie("csrftoken");
    if (csrfToken) {
      finalHeaders.set("X-CSRFToken", csrfToken);
    }
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
