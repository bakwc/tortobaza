import Link from "next/link";
import { Menu } from "lucide-react";

export function Header() {
  const navClass =
    "text-[16px] font-medium uppercase tracking-[0.02em] [font-family:var(--font-base)] hover:opacity-80 transition-opacity";

  return (
    <header className="sticky top-0 z-40 bg-[var(--brand)] text-[var(--brand-foreground)] shadow-sm">
      <div className="site-header-bar flex h-[76px] items-center justify-between gap-4 pr-6">
        <div className="flex min-w-0 items-center gap-6 sm:gap-8 md:gap-10">
          <Link href="/" className="site-header-logo flex items-center" aria-label="Sweet & Chill">
            <img
              src="/sweet-chill-logo-1.svg"
              alt="Sweet & Chill"
              width={1254}
              height={390}
              className="h-16 w-auto"
            />
          </Link>
          <nav
            className="flex flex-wrap items-center gap-x-8 gap-y-2 sm:gap-x-10 md:gap-x-12"
            aria-label="Primary"
          >
            <Link href="/order" className={navClass}>
              Online Store
            </Link>
            <Link href="/contacts" className={navClass}>
              Contacts
            </Link>
            <Link href="/about" className={navClass}>
              About
            </Link>
          </nav>
        </div>
        <button
          type="button"
          className="-mr-2 shrink-0 p-2 hover:opacity-80 transition-opacity"
          aria-label="Menu"
        >
          <Menu className="h-6 w-6" strokeWidth={1.6} />
        </button>
      </div>
    </header>
  );
}
