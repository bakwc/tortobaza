import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { SITE_INFO } from "@/lib/site-info";
import { PUBLIC_SITE_ORIGIN } from "@/lib/site-host";

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
  const defaultPath = pathsByLocale[routing.defaultLocale];
  if (defaultPath) {
    languages["x-default"] = absoluteUrl(
      origin,
      localePath(routing.defaultLocale, defaultPath),
    );
  }
  return { languages };
}

export function localizedPageMetadata(
  locale: Locale,
  path: string,
  title: string,
  description: string,
): Metadata {
  const pathsByLocale = Object.fromEntries(
    routing.locales.map((alternateLocale) => [alternateLocale, path]),
  ) as Record<Locale, string>;
  const localizedPath = localePath(locale, path);

  return {
    title,
    description,
    alternates: {
      canonical: localizedPath,
      ...languageAlternates(PUBLIC_SITE_ORIGIN, pathsByLocale),
    },
    openGraph: {
      title,
      description,
      url: localizedPath,
    },
  };
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

export function localBusinessJsonLd(origin: string) {
  return {
    "@context": "https://schema.org",
    "@type": "Bakery",
    name: SITE_INFO.brand,
    url: origin.replace(/\/$/, ""),
    telephone: SITE_INFO.phone,
    email: SITE_INFO.email,
    address: {
      "@type": "PostalAddress",
      streetAddress: SITE_INFO.address.line1,
      addressLocality: SITE_INFO.address.city,
      addressCountry: "GE",
    },
    sameAs: [SITE_INFO.instagramHref],
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
      hasMerchantReturnPolicy: {
        "@type": "MerchantReturnPolicy",
        applicableCountry: "GE",
        returnPolicyCategory: "https://schema.org/MerchantReturnNotPermitted",
      },
      shippingDetails: {
        "@type": "OfferShippingDetails",
        shippingRate: {
          "@type": "MonetaryAmount",
          value: "5.00",
          currency: SITE_INFO.currency,
        },
        shippingDestination: {
          "@type": "DefinedRegion",
          addressCountry: "GE",
        },
        deliveryTime: {
          "@type": "ShippingDeliveryTime",
          handlingTime: {
            "@type": "QuantitativeValue",
            minValue: 0,
            maxValue: 3,
            unitCode: "DAY",
          },
          transitTime: {
            "@type": "QuantitativeValue",
            minValue: 0,
            maxValue: 1,
            unitCode: "DAY",
          },
        },
      },
    },
  };
}
