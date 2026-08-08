import type { MetadataRoute } from "next";
import { headers } from "next/headers";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";

const PUBLIC_SITE_ORIGIN =
  process.env.PUBLIC_SITE_ORIGIN?.replace(/\/$/, "") ??
  `https://${process.env.PUBLIC_SITE_HOST ?? "sweet-chill.ge"}`;

export default async function robots(): Promise<MetadataRoute.Robots> {
  const headerStore = await headers();
  const host = publicHostFromRequest((name) => headerStore.get(name));
  const isDev = isDevSweetChillHost(host) || host.includes("localhost");

  if (isDev) {
    return {
      rules: {
        userAgent: "*",
        disallow: "/",
      },
    };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/*/checkout",
        "/*/checkout/",
        "/*/orders",
        "/*/orders/",
        "/*/attendance",
        "/*/attendance/",
      ],
    },
    sitemap: `${PUBLIC_SITE_ORIGIN}/sitemap.xml`,
  };
}
