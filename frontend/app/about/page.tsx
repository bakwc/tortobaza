import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export const metadata = {
  title: "About",
  description: `About ${SITE_INFO.brand}, handcrafted cakes and desserts in Batumi.`,
};

export default function AboutPage() {
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
          About us
        </h1>
        <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
          <p>
            {SITE_INFO.brand} makes handcrafted cakes and desserts to order in{" "}
            {SITE_INFO.address.city}, {SITE_INFO.address.country}. We focus on
            quality ingredients, reliable fulfilment times, and clear communication
            for pickup and delivery.
          </p>
          <dl className="space-y-4 rounded-2xl bg-white/50 p-6 ring-1 ring-[var(--line)]">
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                Trading name
              </dt>
              <dd className="m-0">{SITE_INFO.brand}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                Company name
              </dt>
              <dd className="m-0">{SITE_INFO.legalName}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                Company ID
              </dt>
              <dd className="m-0">{SITE_INFO.legalId}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                Email
              </dt>
              <dd className="m-0">
                <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
                  {SITE_INFO.email}
                </Link>
              </dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                Phone
              </dt>
              <dd className="m-0">
                <Link href={SITE_INFO.phoneHref} className="underline underline-offset-2">
                  {SITE_INFO.phone}
                </Link>
              </dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
              <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
                WhatsApp
              </dt>
              <dd className="m-0">
                <Link
                  href={SITE_INFO.whatsappHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-2"
                >
                  {SITE_INFO.phone}
                </Link>
              </dd>
            </div>
          </dl>
          <p>
            Pickup address: {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
            {SITE_INFO.address.country}. Prices on the site are shown in{" "}
            {SITE_INFO.currency}.
          </p>
        </div>
      </article>
    </div>
  );
}
