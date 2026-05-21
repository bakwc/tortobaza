import Image from "next/image";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto bg-[var(--brand)] text-[var(--brand-foreground)]">
      <div className="mx-auto grid max-w-[1400px] gap-8 px-6 py-12 md:grid-cols-[auto_1fr_auto_auto] md:items-center">
        <Link href="/" className="flex items-center" aria-label="Tortobaza">
          <Image
            src="/sweet-chill-logo-1.svg"
            alt="Sweet & Chill"
            width={1020}
            height={390}
            className="h-12 w-auto"
          />
        </Link>
        <nav className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm tracking-wider uppercase md:justify-center">
          <Link href="/delivery-and-refunds" className="hover:opacity-80">
            Delivery &amp; refunds
          </Link>
          <Link href="/privacy" className="hover:opacity-80">
            Privacy
          </Link>
          <Link href="/terms" className="hover:opacity-80">
            Terms
          </Link>
        </nav>
        <div className="flex items-center gap-4">
          <a
            href="https://www.instagram.com/sweet_chill_batumi"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Instagram"
          >
            <Image
              src="/instagram_white.svg"
              alt=""
              width={28}
              height={28}
              className="h-7 w-7"
            />
          </a>
          <a
            href="https://wa.me/995599875273"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="WhatsApp"
          >
            <Image
              src="/whatsapp_white.png"
              alt=""
              width={56}
              height={56}
              className="h-14 w-14"
            />
          </a>
        </div>
        <p className="text-xs opacity-70 md:text-right">
          © {new Date().getFullYear()} Sweet & Chill
        </p>
      </div>
    </footer>
  );
}
