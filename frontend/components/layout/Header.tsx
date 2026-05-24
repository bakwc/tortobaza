import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Menu } from "lucide-react";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";

export async function Header() {
  const t = await getTranslations("nav");

  const navClass =
    "text-[16px] font-medium uppercase tracking-[0.02em] [font-family:var(--font-base)] hover:opacity-80 transition-opacity";

  return (
    <header className="sticky top-0 z-40 bg-[var(--brand)] text-[var(--brand-foreground)] shadow-sm">
      <div className="site-header-bar flex h-[76px] items-center justify-between gap-4 pr-6">
        <div className="flex min-w-0 items-center gap-6 sm:gap-8 md:gap-10">
          <Link href="/" className="site-header-logo flex items-center" aria-label={t("sweetChill")}>
            <img
              src="/sweet-chill-logo-2.svg"
              alt={t("sweetChill")}
              width={1254}
              height={365}
              className="h-16 w-auto"
            />
          </Link>
          <nav
            className="flex flex-wrap items-center gap-x-8 gap-y-2 sm:gap-x-10 md:gap-x-12"
            aria-label={t("primary")}
          >
            <Link href="/order" className={navClass}>
              {t("onlineStore")}
            </Link>
            <Link href="/contacts" className={navClass}>
              {t("contacts")}
            </Link>
            <Link href="/about" className={navClass}>
              {t("about")}
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher invert />
          <button
            type="button"
            className="-mr-2 shrink-0 p-2 hover:opacity-80 transition-opacity"
            aria-label={t("menuAria")}
          >
            <Menu className="h-6 w-6" strokeWidth={1.6} />
          </button>
        </div>
      </div>
    </header>
  );
}
