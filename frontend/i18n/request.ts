import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

function localeFromAcceptLanguage(
  acceptLang: string | null,
  allowed: readonly string[],
): string | undefined {
  if (!acceptLang) return undefined;
  const prefs = acceptLang.split(",").map((part) => {
    const [tag] = part.trim().split(";");
    return tag.trim().toLowerCase();
  });
  for (const pref of prefs) {
    const base = pref.split("-")[0];
    if (!base) continue;
    for (const code of allowed) {
      const c = code.toLowerCase();
      if (pref === c || pref.startsWith(`${c}-`) || base === c) return code;
    }
  }
  return undefined;
}

export default getRequestConfig(async ({ requestLocale }) => {
  const allowed = routing.locales as readonly string[];
  const cookieLocale = (await cookies()).get("NEXT_LOCALE")?.value;

  let locale =
    cookieLocale && allowed.includes(cookieLocale) ? cookieLocale : await requestLocale;

  if (!locale || !allowed.includes(locale)) {
    const fromHeader = localeFromAcceptLanguage((await headers()).get("accept-language"), allowed);
    if (fromHeader) locale = fromHeader;
  }

  if (!locale || !allowed.includes(locale)) {
    locale = routing.defaultLocale;
  }

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
