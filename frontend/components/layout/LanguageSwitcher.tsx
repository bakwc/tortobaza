"use client";

import { useQuery } from "@tanstack/react-query";
import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { api } from "@/lib/api";

export function LanguageSwitcher({
  invert,
}: {
  invert?: boolean;
}) {
  const active = useLocale();
  const pathname = usePathname();
  const categoryMatch = pathname.match(/^\/categories\/([^/]+)$/);
  const pageSlug = categoryMatch?.[1];
  const categoryQuery = useQuery({
    queryKey: ["category-alternates", active, pageSlug],
    queryFn: () => api.getCategory(pageSlug!, active),
    enabled: pageSlug !== undefined,
    staleTime: 300_000,
  });

  const activeBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand-foreground)] text-[var(--brand)]"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand)] text-[var(--brand-foreground)]";

  const inactiveBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--brand-foreground)]/75 hover:bg-white/15"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--ink)]/85 hover:bg-black/[0.05]";

  return (
    <div className="flex shrink-0 items-center gap-1">
      {routing.locales.map((loc) => {
        const localizedSlug = categoryQuery.data?.page_slugs[loc as Locale];
        const href =
          loc === active
            ? pathname
            : pageSlug
              ? localizedSlug
                ? `/categories/${localizedSlug}`
                : "/"
              : pathname;
        return (
          <Link
            key={loc}
            href={href}
            locale={loc}
            className={active === loc ? activeBtn : inactiveBtn}
            aria-pressed={active === loc}
          >
            {loc.toUpperCase()}
          </Link>
        );
      })}
    </div>
  );
}
