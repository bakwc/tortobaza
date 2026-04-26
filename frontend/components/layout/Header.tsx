import Link from "next/link";
import { Menu } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-[var(--brand)] text-[var(--brand-foreground)] shadow-sm">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-6">
        <Link
          href="/"
          className="font-display text-3xl italic tracking-wide leading-none"
          aria-label="Tortobaza"
        >
          Tortobaza
        </Link>
        <button
          type="button"
          className="-mr-2 p-2 hover:opacity-80 transition-opacity"
          aria-label="Menu"
        >
          <Menu className="h-6 w-6" strokeWidth={1.6} />
        </button>
      </div>
    </header>
  );
}
