import type { MetadataRoute } from "next";
import { routing, type Locale } from "@/i18n/routing";
import { sitemapFetch } from "@/lib/api/sitemap-fetch";
import type { Category, ProductsPage } from "@/lib/api/types";
import { absoluteUrl, localePath } from "@/lib/seo";

export const dynamic = "force-dynamic";

const PUBLIC_SITE_ORIGIN =
  process.env.PUBLIC_SITE_ORIGIN?.replace(/\/$/, "") ??
  `https://${process.env.PUBLIC_SITE_HOST ?? "sweet-chill.ge"}`;

const STATIC_PATHS = [
  "/",
  "/order",
  "/about",
  "/contacts",
  "/delivery-and-refunds",
  "/privacy",
  "/terms",
  "/cake-constructor",
];

async function allProducts(locale: string): Promise<ProductsPage["results"]> {
  const results: ProductsPage["results"] = [];
  let page = 1;
  while (true) {
    const data = await sitemapFetch<ProductsPage>("/api/products/", locale, {
      page,
      page_size: 500,
    });
    results.push(...data.results);
    if (!data.next) break;
    page += 1;
  }
  return results;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];

  for (const locale of routing.locales) {
    for (const path of STATIC_PATHS) {
      entries.push({
        url: absoluteUrl(PUBLIC_SITE_ORIGIN, localePath(locale, path)),
        changeFrequency: path === "/order" || path === "/" ? "daily" : "monthly",
        priority: path === "/order" || path === "/" ? 1 : 0.6,
      });
    }
  }

  const categoriesByLocale = await Promise.all(
    routing.locales.map(async (locale) => ({
      locale,
      categories: await sitemapFetch<Category[]>("/api/categories/", locale),
    })),
  );

  for (const { locale, categories } of categoriesByLocale) {
    for (const category of categories) {
      if (!category.page_slug) continue;
      entries.push({
        url: absoluteUrl(
          PUBLIC_SITE_ORIGIN,
          localePath(locale, `/categories/${category.page_slug}`),
        ),
        lastModified: category.updated_at,
        changeFrequency: "daily",
        priority: 0.9,
      });
    }
  }

  const products = await allProducts(routing.defaultLocale);
  for (const product of products) {
    for (const locale of routing.locales) {
      entries.push({
        url: absoluteUrl(
          PUBLIC_SITE_ORIGIN,
          localePath(locale as Locale, `/order/${product.slug}`),
        ),
        changeFrequency: "weekly",
        priority: 0.8,
      });
    }
  }

  return entries;
}
