import Link from "next/link";

export function DevBanner() {
  return (
    <div
      role="banner"
      className="relative z-50 border-b border-red-950/25 bg-red-600 px-4 py-2 text-center text-xs leading-snug text-white sm:text-sm"
    >
      <span className="inline-block sm:mr-2">
        This is a development site. Do not place real orders or share this URL.
      </span>
      <Link
        href="https://sweet-chill.ge"
        className="inline-block font-semibold underline underline-offset-2 hover:text-white/90"
      >
        Go to sweet-chill.ge
      </Link>
    </div>
  );
}
