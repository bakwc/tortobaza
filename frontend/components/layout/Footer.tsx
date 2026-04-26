import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto bg-[var(--brand)] text-[var(--brand-foreground)]">
      <div className="mx-auto grid max-w-[1400px] gap-8 px-6 py-12 md:grid-cols-[auto_1fr_auto] md:items-start">
        <Link href="/" className="font-display text-3xl italic" aria-label="Tortobaza">
          Tortobaza
        </Link>
        <nav className="flex flex-wrap items-center gap-6 text-sm tracking-wider uppercase md:justify-center">
          <Link href="/" className="hover:opacity-80">
            Online store
          </Link>
          <Link href="/order" className="hover:opacity-80">
            Order
          </Link>
          <Link href="/" className="hover:opacity-80">
            Contacts
          </Link>
        </nav>
        <p className="text-xs opacity-70 md:text-right">
          © {new Date().getFullYear()} Tortobaza
        </p>
      </div>
    </footer>
  );
}
