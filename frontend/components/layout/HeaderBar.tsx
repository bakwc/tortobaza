"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Menu, X } from "lucide-react";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";

const navLinks = [
  { href: "/order", labelKey: "onlineStore" },
  { href: "/contacts", labelKey: "contacts" },
  { href: "/about", labelKey: "about" },
] as const;

export function HeaderBar() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const navClass =
    "text-[16px] font-medium uppercase tracking-[0.02em] [font-family:var(--font-base)] hover:opacity-80 transition-opacity";

  const mobileNavClass =
    "text-[28px] font-medium uppercase tracking-[0.02em] [font-family:var(--font-base)] hover:opacity-80 transition-opacity";

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
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
            className="hidden md:flex items-center gap-x-12"
            aria-label={t("primary")}
          >
            {navLinks.map((link) => (
              <Link key={link.href} href={link.href} className={navClass}>
                {t(link.labelKey)}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher invert />
          <button
            type="button"
            className="-mr-2 shrink-0 p-2 hover:opacity-80 transition-opacity md:hidden"
            aria-label={t("menuAria")}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? (
              <X className="h-6 w-6" strokeWidth={1.6} />
            ) : (
              <Menu className="h-6 w-6" strokeWidth={1.6} />
            )}
          </button>
        </div>
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex flex-col bg-[var(--brand)] text-[var(--brand-foreground)] md:hidden">
          <div className="flex h-[76px] items-center justify-end gap-2 pr-6">
            <LanguageSwitcher invert />
            <button
              type="button"
              className="-mr-2 shrink-0 p-2 hover:opacity-80 transition-opacity"
              aria-label={t("menuAria")}
              onClick={() => setOpen(false)}
            >
              <X className="h-6 w-6" strokeWidth={1.6} />
            </button>
          </div>
          <nav
            className="flex flex-1 flex-col items-center justify-center gap-10 px-6 pb-[76px]"
            aria-label={t("primary")}
          >
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={mobileNavClass}
                onClick={() => setOpen(false)}
              >
                {t(link.labelKey)}
              </Link>
            ))}
          </nav>
        </div>
      ) : null}
    </>
  );
}
