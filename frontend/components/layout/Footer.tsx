import Image from "next/image";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto bg-[var(--brand)] text-[var(--brand-foreground)]">
      <div className="mx-auto grid max-w-[1400px] gap-8 px-6 py-12 md:grid-cols-[auto_1fr_auto] md:items-center">
        <Link href="/" className="flex items-center" aria-label="Tortobaza">
          <Image
            src="/sweet_chill_logo_1.jpg"
            alt="Sweet & Chill"
            width={1955}
            height={544}
            className="h-12 w-auto"
          />
        </Link>
        <nav className="flex flex-wrap items-center gap-6 text-sm tracking-wider uppercase md:justify-center">
          <Link href="/order" className="hover:opacity-80">
            Online store
          </Link>
          <Link href="/contacts" className="hover:opacity-80">
            Contacts
          </Link>
        </nav>
        <p className="text-xs opacity-70 md:text-right">
          © {new Date().getFullYear()} Sweet & Chill
        </p>
      </div>
    </footer>
  );
}
