import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { SITE_INFO } from "@/lib/site-info";

export function absoluteUrl(origin: string, path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${origin.replace(/\/$/, "")}${normalized}`;
}

export function localePath(locale: Locale, path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `/${locale}${normalized === "/" ? "" : normalized}`;
}

export function languageAlternates(
  origin: string,
  pathsByLocale: Partial<Record<Locale, string>>,
): Metadata["alternates"] {
  const languages: Record<string, string> = {};
  for (const locale of routing.locales) {
    const path = pathsByLocale[locale];
    if (!path) continue;
    languages[locale] = absoluteUrl(origin, localePath(locale, path));
  }
  return { languages };
}

export function jsonLdScript(data: Record<string, unknown> | Record<string, unknown>[]) {
  return {
    __html: JSON.stringify(data),
  };
}

export function breadcrumbJsonLd(
  origin: string,
  items: { name: string; path: string }[],
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: absoluteUrl(origin, item.path),
    })),
  };
}

export function itemListJsonLd(
  origin: string,
  name: string,
  items: { name: string; path: string }[],
) {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name,
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      url: absoluteUrl(origin, item.path),
    })),
  };
}

export function productJsonLd(input: {
  origin: string;
  name: string;
  description: string;
  path: string;
  imageUrls: string[];
  price: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: input.name,
    description: input.description,
    url: absoluteUrl(input.origin, input.path),
    image: input.imageUrls,
    brand: {
      "@type": "Brand",
      name: SITE_INFO.brand,
    },
    offers: {
      "@type": "Offer",
      url: absoluteUrl(input.origin, input.path),
      priceCurrency: SITE_INFO.currency,
      price: input.price,
      availability: "https://schema.org/InStock",
    },
  };
}
