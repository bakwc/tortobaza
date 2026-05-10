import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export const metadata = {
  title: "Terms & Conditions",
  description: `Terms of use for ${SITE_INFO.brand}.`,
};

export default function TermsPage() {
  return (
    <div className="bg-[var(--cream)]">
      <article className="mx-auto max-w-[820px] px-6 py-14 text-[var(--ink)] md:py-20">
        <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
          Terms &amp; Conditions
        </h1>
        <p className="mt-6 text-sm text-[var(--ink)]/70">
          Last updated: {new Date().toISOString().slice(0, 10)}
        </p>
        <div className="mt-8 space-y-6 text-base leading-relaxed md:text-lg">
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Provider
            </h2>
            <p>
              The website and online ordering are provided by{" "}
              <span className="font-semibold">{SITE_INFO.legalName}</span> (ID{" "}
              {SITE_INFO.legalId}), trading as {SITE_INFO.brand}. Address:{" "}
              {SITE_INFO.address.line1}, {SITE_INFO.address.city},{" "}
              {SITE_INFO.address.country}.{" "}
              <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
                {SITE_INFO.email}
              </Link>
              ,{" "}
              <Link href={SITE_INFO.phoneHref} className="underline underline-offset-2">
                {SITE_INFO.phone}
              </Link>
              .
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Orders and prices
            </h2>
            <p>
              By submitting an order you offer to buy the items in your cart at the
              prices shown at checkout. All prices are in {SITE_INFO.currency}. We
              confirm acceptance when your order is accepted and becomes payable
              according to the flow shown on the site.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Payment
            </h2>
            <p>
              Card payments are processed through our bank or authorized payment
              partner. You authorise us to charge the selected payment method for the
              total shown, including applicable taxes and fees if disclosed.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Pickup and delivery
            </h2>
            <p>
              Fulfilment options, time slots, and handover rules are described on the{" "}
              <Link href="/delivery-and-refunds" className="underline underline-offset-2">
                Delivery &amp; refunds
              </Link>{" "}
              page.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Limitation
            </h2>
            <p>
              To the maximum extent permitted by law, we are not liable for indirect
              or consequential loss. Nothing in these terms excludes liability that
              cannot be excluded under applicable consumer law.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Law
            </h2>
            <p>
              These terms are governed by the laws of Georgia. Courts in{" "}
              {SITE_INFO.address.city} have non-exclusive jurisdiction.
            </p>
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">
              Privacy
            </h2>
            <p>
              See our{" "}
              <Link href="/privacy" className="underline underline-offset-2">
                Privacy Policy
              </Link>
              .
            </p>
          </section>
        </div>
      </article>
    </div>
  );
}
