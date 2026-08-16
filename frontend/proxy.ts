import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const handleI18nRouting = createMiddleware(routing);
const localePattern = new RegExp(`^/(${routing.locales.join("|")})(/|$)`);

export const config = {
  matcher: "/((?!api|trpc|_next|_vercel|media|.*\\..*).*)",
};

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const localeMatch = pathname.match(localePattern);

  if (!localeMatch) {
    const destination =
      pathname === "/"
        ? `/${routing.defaultLocale}`
        : `/${routing.defaultLocale}${pathname}`;
    return NextResponse.redirect(new URL(destination, request.url), 308);
  }

  const locale = localeMatch[1];
  if (pathname === `/${locale}/order` || pathname === `/${locale}/order/`) {
    return NextResponse.redirect(new URL(`/${locale}`, request.url), 308);
  }

  return handleI18nRouting(request);
}
