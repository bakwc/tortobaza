import Link from "next/link";
import { SITE_INFO } from "@/lib/site-info";

export default function DeliveryContentEn({ updatedLine }: { updatedLine: string }) {
  return (
    <>
      <h1 className="text-2xl font-bold tracking-[0.06em] uppercase md:text-3xl">
        Delivery, returns, cancellation &amp; refunds
      </h1>
      <p className="mt-6 text-sm text-[var(--ink)]/70">{updatedLine}</p>
      <div className="mt-8 space-y-8 text-base leading-relaxed md:text-lg">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Delivery</h2>
          <p>
            We deliver within {SITE_INFO.address.city} and surrounding areas as offered at checkout.
            Delivery time is the slot you select; if we cannot meet it we contact you using the details
            you provided. Delivery fees, if any, appear before payment.
          </p>
          <p>
            Risk passes to you when the order is handed over to you or your nominated recipient at the
            address or pickup point.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Pickup</h2>
          <p>
            For pickup, bring your order reference if we provide one. Hours and location are on our{" "}
            <Link href="/contacts" className="underline underline-offset-2">
              Contacts
            </Link>{" "}
            page.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Cancellation</h2>
          <p>
            You may cancel free of charge if we have not yet started production for your order.
            Contact us as soon as possible at{" "}
            <Link href={`mailto:${SITE_INFO.email}`} className="underline underline-offset-2">
              {SITE_INFO.email}
            </Link>{" "}
            or{" "}
            <Link
              href={SITE_INFO.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              WhatsApp
            </Link>{" "}
            with your order number. If production has started, cancellation may not be possible in
            full; we will confirm the options available.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Returns</h2>
          <p>
            Cakes and desserts are perishable and made to order. There is no right of return for change
            of mind after handover. If there is a quality defect or a clear error on our side, report it
            at handover or within two hours with a photo where helpful; we arrange an appropriate remedy.
          </p>
        </section>
        <section className="space-y-3">
          <h2 className="text-lg font-semibold tracking-wide uppercase md:text-xl">Refunds</h2>
          <p>
            Approved refunds for card payments are returned to the original card within fourteen business
            days after approval, depending on your bank. If you paid another way, we refund using the same
            method where possible.
          </p>
          <p>
            No refund is due after you accept a non-defective perishable order, except where required by
            law.
          </p>
        </section>
      </div>
    </>
  );
}
