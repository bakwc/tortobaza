import "server-only";
import { headers } from "next/headers";
import { isDevSweetChillHost, publicHostFromRequest } from "@/lib/site-host";

export async function getPublicSiteOrigin(): Promise<string> {
  if (process.env.PUBLIC_SITE_ORIGIN) {
    return process.env.PUBLIC_SITE_ORIGIN.replace(/\/$/, "");
  }
  if (process.env.PUBLIC_SITE_HOST) {
    return `https://${process.env.PUBLIC_SITE_HOST}`;
  }
  const headerStore = await headers();
  const host = publicHostFromRequest((name) => headerStore.get(name));
  const protocol = host.includes("localhost") || isDevSweetChillHost(host) ? "http" : "https";
  if (host.includes("localhost")) {
    return `${protocol}://${host || "localhost:3000"}`;
  }
  if (isDevSweetChillHost(host)) {
    return `https://${host}`;
  }
  return `https://${host || "sweet-chill.ge"}`;
}
