import "server-only";

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";
const PUBLIC_SITE_HOST = process.env.PUBLIC_SITE_HOST ?? "sweet-chill.ge";

export async function sitemapFetch<T>(
  path: string,
  locale: string,
  searchParams?: Record<string, string | number>,
): Promise<T> {
  const url = new URL(path.replace(/^\//, ""), `${BACKEND_ORIGIN}/`);
  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "Accept-Language": locale,
      "X-Forwarded-Host": PUBLIC_SITE_HOST,
      "X-Forwarded-Proto": "https",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Sitemap fetch failed for ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}
