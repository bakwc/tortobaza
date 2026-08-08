import "server-only";
import { headers } from "next/headers";
import { getLocale } from "next-intl/server";
import { ApiError } from "./client";

export type PublicServerFetchOptions = RequestInit & {
  searchParams?: Record<string, string | number | undefined | null>;
  next?: { revalidate?: number; tags?: string[] };
};

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";
const PUBLIC_SITE_HOST = process.env.PUBLIC_SITE_HOST;
const CATALOG_REVALIDATE_SECONDS = 300;

function buildUrl(path: string, searchParams?: PublicServerFetchOptions["searchParams"]) {
  const url = new URL(path.replace(/^\//, ""), `${BACKEND_ORIGIN}/`);
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url;
}

export async function publicServerFetch<T>(
  path: string,
  {
    searchParams,
    headers: extraHeaders,
    next,
    ...init
  }: PublicServerFetchOptions = {},
): Promise<T> {
  const url = buildUrl(path, searchParams);
  const finalHeaders = new Headers(extraHeaders);
  if (!finalHeaders.has("Accept")) {
    finalHeaders.set("Accept", "application/json");
  }
  if (!finalHeaders.has("Accept-Language")) {
    finalHeaders.set("Accept-Language", await getLocale());
  }

  if (PUBLIC_SITE_HOST) {
    finalHeaders.set("X-Forwarded-Host", PUBLIC_SITE_HOST);
    finalHeaders.set("X-Forwarded-Proto", "https");
  } else {
    const incoming = await headers();
    const exposedHost = incoming.get("x-forwarded-host") ?? incoming.get("host");
    if (exposedHost) {
      finalHeaders.set("X-Forwarded-Host", exposedHost);
    }
    finalHeaders.set(
      "X-Forwarded-Proto",
      incoming.get("x-forwarded-proto") ?? "http",
    );
  }

  const response = await fetch(url, {
    ...init,
    headers: finalHeaders,
    next: next ?? { revalidate: CATALOG_REVALIDATE_SECONDS, tags: ["catalog"] },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
