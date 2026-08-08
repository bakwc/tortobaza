"use client";

import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { routing, type Locale } from "@/i18n/routing";
import { useLocaleAlternates } from "@/lib/locale-alternates";

export function LanguageSwitcher({
  invert,
}: {
  invert?: boolean;
}) {
  const active = useLocale();
  const pathname = usePathname();
  const alternates = useLocaleAlternates();

  const activeBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand-foreground)] text-[var(--brand)]"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand)] text-[var(--brand-foreground)]";

  const inactiveBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--brand-foreground)]/75 hover:bg-white/15"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--ink)]/85 hover:bg-black/[0.05]";

  return (
    <div className="flex shrink-0 items-center gap-1">
      {routing.locales.map((loc) => {
        const href = alternates?.[loc as Locale] ?? pathname;
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
