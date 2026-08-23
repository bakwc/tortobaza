import type { MetadataRoute } from "next";
import { routing, type Locale } from "@/i18n/routing";
import { sitemapFetch } from "@/lib/api/sitemap-fetch";
import type { Category, CategoryLanding, ProductsPage } from "@/lib/api/types";
import { absoluteUrl, localePath } from "@/lib/seo";
import { PUBLIC_SITE_ORIGIN } from "@/lib/site-host";

export const dynamic = "force-dynamic";

const STATIC_PATHS = [
  "/",
  "/about",
  "/contacts",
  "/delivery-and-refunds",
  "/privacy",
  "/terms",
  "/cake-constructor",
];

function sitemapAlternates(
  paths: Partial<Record<Locale, string>>,
): { languages: Record<string, string> } {
  const languages: Record<string, string> = {};
  for (const locale of routing.locales) {
    const path = paths[locale];
    if (!path) continue;
    languages[locale] = absoluteUrl(
      PUBLIC_SITE_ORIGIN,
      localePath(locale, path),
    );
  }
  const defaultPath = paths[routing.defaultLocale];
  if (defaultPath) {
    languages["x-default"] = absoluteUrl(
      PUBLIC_SITE_ORIGIN,
      localePath(routing.defaultLocale, defaultPath),
    );
  }
  return { languages };
}

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
        alternates: sitemapAlternates(
          Object.fromEntries(
            routing.locales.map((alternateLocale) => [alternateLocale, path]),
          ) as Record<Locale, string>,
        ),
        changeFrequency: path === "/" ? "daily" : "monthly",
        priority: path === "/" ? 1 : 0.6,
      });
    }
  }

  const [categoriesByLocale, landingsByLocale] = await Promise.all([
    Promise.all(
      routing.locales.map(async (locale) => ({
        locale,
        categories: await sitemapFetch<Category[]>("/api/categories/", locale),
      })),
    ),
    Promise.all(
      routing.locales.map(async (locale) => ({
        locale,
        landings: await sitemapFetch<CategoryLanding[]>(
          "/api/category-landings/",
          locale,
        ),
      })),
    ),
  ]);

  for (const { locale, categories } of categoriesByLocale) {
    for (const category of categories) {
      if (!category.page_slug) continue;
      entries.push({
        url: absoluteUrl(
          PUBLIC_SITE_ORIGIN,
          localePath(locale, `/categories/${category.page_slug}`),
        ),
        alternates: sitemapAlternates(
          Object.fromEntries(
            routing.locales
              .filter((alternateLocale) => category.page_slugs[alternateLocale])
              .map((alternateLocale) => [
                alternateLocale,
                `/categories/${category.page_slugs[alternateLocale]}`,
              ]),
          ) as Partial<Record<Locale, string>>,
        ),
        lastModified: category.updated_at,
        changeFrequency: "daily",
        priority: 0.9,
      });
    }
  }

  for (const { locale, landings } of landingsByLocale) {
    for (const landing of landings) {
      if (!landing.page_slug) continue;
      entries.push({
        url: absoluteUrl(
          PUBLIC_SITE_ORIGIN,
          localePath(locale, `/categories/${landing.page_slug}`),
        ),
        alternates: sitemapAlternates(
          Object.fromEntries(
            routing.locales
              .filter((alternateLocale) => landing.page_slugs[alternateLocale])
              .map((alternateLocale) => [
                alternateLocale,
                `/categories/${landing.page_slugs[alternateLocale]}`,
              ]),
          ) as Partial<Record<Locale, string>>,
        ),
        lastModified: landing.updated_at,
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
        alternates: sitemapAlternates(
          Object.fromEntries(
            routing.locales.map((alternateLocale) => [
              alternateLocale,
              `/order/${product.slug}`,
            ]),
          ) as Record<Locale, string>,
        ),
        changeFrequency: "weekly",
        priority: 0.8,
      });
    }
  }

  return entries;
}
