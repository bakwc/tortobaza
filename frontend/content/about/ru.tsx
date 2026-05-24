import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function AboutContentRu() {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">О нас</h1>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <p>
          {SITE_INFO.brand} готовит торты и десерты на заказ в {SITE_INFO.address.city},{" "}
          {SITE_INFO.address.country}. Мы уделяем внимание качеству ингредиентов, срокам выполнения
          заказов и понятной коммуникации при самовывозе и доставке.
        </p>
        <dl className="space-y-4 rounded-2xl bg-white/50 p-6 ring-1 ring-[var(--line)]">
          <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
            <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
              Торговое наименование
            </dt>
            <dd className="m-0">{SITE_INFO.brand}</dd>
          </div>
          <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
            <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
              Юридическое название
            </dt>
            <dd className="m-0">{SITE_INFO.legalName}</dd>
          </div>
          <div className="grid gap-1 sm:grid-cols-[11rem_1fr] sm:gap-x-6 sm:items-baseline">
            <dt className="text-sm font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/70">
              Идентификатор компании
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
              Телефон
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
          Адрес самовывоза: {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
          {SITE_INFO.address.country}. Цены на сайте указаны в {SITE_INFO.currency}.
        </p>
      </div>
    </>
  );
}
