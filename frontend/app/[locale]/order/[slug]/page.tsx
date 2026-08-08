import type { Metadata } from "next";
import { ChevronLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { ItemDetail } from "@/components/item/ItemDetail";
import { Breadcrumbs } from "@/components/seo/Breadcrumbs";
import { JsonLd } from "@/components/seo/JsonLd";
import { ApiError } from "@/lib/api/client";
import { publicApi } from "@/lib/api/public-api";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import {
  breadcrumbJsonLd,
  languageAlternates,
  localePath,
  productJsonLd,
} from "@/lib/seo";
import { getPublicSiteOrigin } from "@/lib/site-origin";

export const revalidate = 300;

async function loadProduct(slug: string) {
  try {
    return await publicApi.getProduct(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const product = await loadProduct(slug);
  if (!product) {
    const tStatic = await getTranslations({ locale, namespace: "metadata" });
    return { title: tStatic("orderTitle") };
  }

  const origin = await getPublicSiteOrigin();
  const path = `/order/${product.slug}`;
  const description = product.description.slice(0, 160) || product.name;
  const pathsByLocale = Object.fromEntries(
    routing.locales.map((loc) => [loc, path]),
  ) as Record<Locale, string>;
  const image = product.images[0]?.image.src;

  return {
    title: product.name,
    description,
    alternates: {
      canonical: localePath(locale as Locale, path),
      ...languageAlternates(origin, pathsByLocale),
    },
    openGraph: {
      title: product.name,
      description,
      url: localePath(locale as Locale, path),
      images: image ? [{ url: image, alt: product.name }] : undefined,
    },
  };
}

export default async function ItemPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);

  const product = await loadProduct(slug);
  if (!product) {
    notFound();
  }

  const [origin, tCheckout, tBreadcrumbs] = await Promise.all([
    getPublicSiteOrigin(),
    getTranslations("checkout"),
    getTranslations("breadcrumbs"),
  ]);

  const localeTyped = locale as Locale;
  const productPath = localePath(localeTyped, `/order/${product.slug}`);
  const categoryHref = product.category.page_slug
    ? `/categories/${product.category.page_slug}`
    : "/order";
  const categoryPath = localePath(localeTyped, categoryHref);
  const backHref = categoryHref;
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-6">
        <JsonLd
          data={[
            breadcrumbJsonLd(origin, [
              { name: tBreadcrumbs("home"), path: localePath(localeTyped, "/") },
              { name: tBreadcrumbs("catalog"), path: localePath(localeTyped, "/order") },
              { name: product.category.name, path: categoryPath },
              { name: product.name, path: productPath },
            ]),
            productJsonLd({
              origin,
              name: product.name,
              description: product.description || product.name,
              path: productPath,
              imageUrls: product.images.map((image) => image.image.src),
              price: product.base_price,
            }),
          ]}
        />
        <div className="mb-4 space-y-3">
          <Breadcrumbs
            items={[
              { name: tBreadcrumbs("home"), href: "/" },
              { name: tBreadcrumbs("catalog"), href: "/order" },
              { name: product.category.name, href: categoryHref },
              { name: product.name },
            ]}
          />
          <Link
            href={backHref}
            className="inline-flex items-center gap-1 text-sm text-[var(--ink)]/70 hover:text-[var(--ink)]"
          >
            <ChevronLeft className="h-4 w-4" />
            {tCheckout("backToCatalog")}
          </Link>
        </div>
        <div className="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-[var(--line)]">
          <ItemDetail product={product} variant="page" />
        </div>
    </div>
  );
}
