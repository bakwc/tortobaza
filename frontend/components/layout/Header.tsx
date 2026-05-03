import Image from "next/image";
import Link from "next/link";
import { Menu } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-[var(--brand)] text-[var(--brand-foreground)] shadow-sm">
      <div className="flex h-[76px] items-center justify-between pr-6">
        <Link href="/" className="flex h-full items-center" aria-label="Tortobaza">
          <Image
            src="/sweet_chill_logo_1.jpg"
            alt="Tortobaza"
            width={1955}
            height={544}
            priority
            className="h-full w-auto"
          />
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
