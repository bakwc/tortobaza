import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { SITE_INFO } from "@/lib/site-info";
import { MAP_EMBED, MAP_LINK } from "@/content/contacts/embed";
import { InfoColumn } from "@/content/contacts/InfoColumn";
import { InstagramIcon, WhatsAppIcon } from "@/content/contacts/icons";

export default function ContactsContentEn() {
  return (
    <>
      <section className="mx-auto max-w-[1100px] px-6 pt-16 pb-10 text-center md:pt-20 md:pb-12">
        <h1 className="text-2xl font-bold tracking-[0.06em] uppercase text-[var(--ink)] md:text-3xl">
          Pickup location
        </h1>
        <p className="mx-auto mt-5 max-w-[640px] text-base leading-relaxed text-[var(--ink)] md:text-lg">
          We don&apos;t have dine-in service or a dessert display, but you&apos;re always welcome to
          pick up your order.
        </p>
      </section>

      <section className="relative">
        <div className="relative h-[420px] w-full overflow-hidden md:h-[520px]">
          <iframe
            title="Pickup location map"
            src={MAP_EMBED}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="h-full w-full grayscale-[1] contrast-[0.95]"
            style={{ border: 0, filter: "grayscale(1) contrast(0.95) opacity(0.85)" }}
          />
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <a
              href={MAP_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="pointer-events-auto inline-flex h-24 w-44 items-center justify-center rounded-full bg-[#5e5e5e]/85 text-[15px] font-medium tracking-[0.06em] uppercase text-white shadow-lg backdrop-blur-sm transition hover:bg-[#4a4a4a]"
            >
              Open Maps
            </a>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-6 py-14 md:py-20">
        <div className="grid gap-12 text-center sm:grid-cols-2 lg:grid-cols-3 lg:gap-8 xl:grid-cols-6">
          <InfoColumn icon={<Clock strokeWidth={1.4} className="h-12 w-12" />} title="Monday – Sunday">
            <p>
              <span className="font-semibold">Store hours:</span> 11:00–21:00
            </p>
            <p>
              <span className="font-semibold">Manager hours:</span> 11:00–21:00
            </p>
          </InfoColumn>

          <InfoColumn icon={<MapPin strokeWidth={1.4} className="h-12 w-12" />} title="Address">
            <p>{SITE_INFO.address.line1}</p>
            <p>
              {SITE_INFO.address.city}, {SITE_INFO.address.country}
            </p>
          </InfoColumn>

          <InfoColumn icon={<Phone strokeWidth={1.4} className="h-12 w-12" />} title="Phone">
            <a href={SITE_INFO.phoneHref} className="hover:opacity-80">
              {SITE_INFO.phone}
            </a>
          </InfoColumn>

          <InfoColumn icon={<Mail strokeWidth={1.4} className="h-12 w-12" />} title="Email">
            <a href={`mailto:${SITE_INFO.email}`} className="hover:opacity-80">
              {SITE_INFO.email}
            </a>
          </InfoColumn>

          <InfoColumn icon={<InstagramIcon className="h-12 w-12" />} title="Instagram">
            <a
              href={SITE_INFO.instagramHref}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80"
            >
              @sweet_chill_batumi
            </a>
          </InfoColumn>

          <InfoColumn icon={<WhatsAppIcon className="h-12 w-12" />} title="WhatsApp">
            <a
              href={SITE_INFO.whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80"
            >
              {SITE_INFO.phone}
            </a>
          </InfoColumn>
        </div>
      </section>
    </>
  );
}
