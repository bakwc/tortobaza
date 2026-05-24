import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function PrivacyContentEn({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">Privacy Policy</h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Who we are</h2>
          <p>
            {SITE_INFO.brand} is operated by <span className="font-semibold">{SITE_INFO.legalName}</span>{" "}
            (ID {SITE_INFO.legalId}), {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
            {SITE_INFO.address.country}. Contact:{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            .
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Data we collect</h2>
          <p>
            When you place an order we typically collect your name, phone number, email address,
            delivery or pickup details, order contents, payment-related references from the bank or
            payment service provider, and any message you add to the order.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Why we use it</h2>
          <p>
            We use this information to confirm and fulfil your order, communicate about timing or
            issues, process card payments with our bank or payment partner, comply with legal
            obligations, and improve our service.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Sharing</h2>
          <p>
            We share data with service providers strictly as needed: payment processing (bank or card
            acquirer), hosting or IT vendors, and delivery staff or contractors when you choose
            delivery. We do not sell your personal data.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Retention</h2>
          <p>
            We keep order and payment records as long as required for accounting, tax, and dispute
            resolution, then delete or anonymise them when the retention period ends.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Your rights</h2>
          <p>
            Under applicable law you may have access, correction, erasure, or restriction rights. To
            exercise these, contact us at{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>
            . We will respond within a reasonable time.
          </p>
        </section>
      </div>
    </>
  );
}
