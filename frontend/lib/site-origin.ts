import "server-only";
import { PUBLIC_SITE_ORIGIN } from "@/lib/site-host";

export async function getPublicSiteOrigin(): Promise<string> {
  return PUBLIC_SITE_ORIGIN;
}
