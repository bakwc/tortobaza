import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["en", "ka", "ru"],
  defaultLocale: "en",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];
