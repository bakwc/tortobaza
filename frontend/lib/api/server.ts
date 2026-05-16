import "server-only";
import { cookies, headers } from "next/headers";

export type ServerFetchOptions = RequestInit & {
  searchParams?: Record<string, string | number | undefined | null>;
};

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

function buildUrl(path: string, searchParams?: ServerFetchOptions["searchParams"]) {
  const url = new URL(path.replace(/^\//, ""), `${BACKEND_ORIGIN}/`);
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url;
}

export async function serverFetch<T>(
  path: string,
  { searchParams, headers: extraHeaders, ...init }: ServerFetchOptions = {},
): Promise<T> {
  const cookieStore = await cookies();
  const cartToken = cookieStore.get("cart_token")?.value;

  const url = buildUrl(path, searchParams);

  const finalHeaders = new Headers(extraHeaders);
  if (!finalHeaders.has("Accept")) {
    finalHeaders.set("Accept", "application/json");
  }
  if (cartToken) {
    finalHeaders.set("X-Cart-Token", cartToken);
    finalHeaders.set("Cookie", `cart_token=${cartToken}`);
  }

  const incoming = await headers();
  const exposedHost = incoming.get("x-forwarded-host") ?? incoming.get("host");
  if (exposedHost) {
    finalHeaders.set("X-Forwarded-Host", exposedHost);
  }
  finalHeaders.set("X-Forwarded-Proto", incoming.get("x-forwarded-proto") ?? "http");

  const response = await fetch(url, {
    ...init,
    headers: finalHeaders,
    cache: init.cache ?? "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request to ${path} failed (${response.status}): ${text}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getServerCartToken(): Promise<string | undefined> {
  const cookieStore = await cookies();
  return cookieStore.get("cart_token")?.value;
}

export async function getServerOrigin(): Promise<string> {
  const headerStore = await headers();
  const proto = headerStore.get("x-forwarded-proto") ?? "http";
  const host = headerStore.get("host") ?? "localhost:3000";
  return `${proto}://${host}`;
}
