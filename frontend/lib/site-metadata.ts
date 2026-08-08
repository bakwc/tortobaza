import type { Metadata } from "next";
import { headers } from "next/headers";
import { getLocale, getTranslations } from "next-intl/server";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";
import { SITE_INFO } from "@/lib/site-info";
import { PUBLIC_SITE_ORIGIN } from "@/lib/site-url";

const OG_IMAGE_PATH = "/sweet_chill_logo_1.jpg";
const OG_IMAGE_WIDTH = 1955;
const OG_IMAGE_HEIGHT = 544;

export async function buildRootMetadata(): Promise<Metadata> {
  const [t, locale, headerStore] = await Promise.all([
    getTranslations("metadata"),
    getLocale(),
    headers(),
  ]);
  const host = publicHostFromRequest((name) => headerStore.get(name));
  const metadataBase = new URL(PUBLIC_SITE_ORIGIN);
  const isDev = isDevSweetChillHost(host);
  const title = t("rootDefaultTitle");
  const description = t("rootDescription");

  return {
    metadataBase,
    title: {
      default: title,
      template: `${SITE_INFO.brand} | %s`,
    },
    description,
    applicationName: SITE_INFO.brand,
    keywords: t("rootKeywords"),
    authors: [{ name: SITE_INFO.brand, url: metadataBase.origin }],
    creator: SITE_INFO.brand,
    publisher: SITE_INFO.brand,
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    openGraph: {
      type: "website",
      locale,
      url: `${metadataBase.origin}/${locale}`,
      siteName: SITE_INFO.brand,
      title,
      description,
      images: [
        {
          url: OG_IMAGE_PATH,
          width: OG_IMAGE_WIDTH,
          height: OG_IMAGE_HEIGHT,
          alt: title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [OG_IMAGE_PATH],
    },
    robots: isDev
      ? { index: false, follow: false, googleBot: { index: false, follow: false } }
      : { index: true, follow: true, googleBot: { index: true, follow: true } },
  };
}
