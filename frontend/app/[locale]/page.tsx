import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { CatalogPage } from "@/components/catalog/CatalogPage";
import type { Locale } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { languageAlternates, localePath } from "@/lib/seo";
import { getPublicSiteOrigin } from "@/lib/site-origin";

export const revalidate = 300;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  setRequestLocale(locale);
  const [t, origin] = await Promise.all([
    getTranslations("metadata"),
    getPublicSiteOrigin(),
  ]);
  const pathsByLocale = Object.fromEntries(
    routing.locales.map((loc) => [loc, "/"]),
  ) as Record<Locale, string>;
  const path = localePath(locale as Locale, "/");
  const title = t("homeTitle");
  const description = t("homeDescription");
  return {
    title: { absolute: title },
    description,
    alternates: {
      canonical: path,
      ...languageAlternates(origin, pathsByLocale),
    },
    openGraph: {
      title,
      description,
      url: path,
    },
  };
}

export default async function HomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <CatalogPage />;
}
