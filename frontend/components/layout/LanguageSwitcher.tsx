"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { routing } from "@/i18n/routing";

const NEXT_LOCALE = "NEXT_LOCALE";

export function LanguageSwitcher({
  invert,
}: {
  invert?: boolean;
}) {
  const router = useRouter();
  const active = useLocale();
  const [pending, startTransition] = useTransition();

  const activeBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand-foreground)] text-[var(--brand)]"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide bg-[var(--brand)] text-[var(--brand-foreground)]";

  const inactiveBtn = invert
    ? "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--brand-foreground)]/75 hover:bg-white/15"
    : "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide text-[var(--ink)]/85 hover:bg-black/[0.05]";

  return (
    <div className={`flex shrink-0 items-center gap-1 ${pending ? "opacity-70" : ""}`}>
      {routing.locales.map((loc) => (
        <button
          key={loc}
          type="button"
          onClick={() => {
            const maxAge = 60 * 60 * 24 * 365;
            document.cookie = `${NEXT_LOCALE}=${loc}; path=/; max-age=${maxAge}; SameSite=Lax`;
            startTransition(() => router.refresh());
          }}
          className={active === loc ? activeBtn : inactiveBtn}
          aria-pressed={active === loc}
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
