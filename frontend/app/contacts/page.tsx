import { Clock, MapPin } from "lucide-react";

export const metadata = {
  title: "Contacts",
  description:
    "Pickup location, working hours and WhatsApp contact for Sweet & Chill.",
};

const ADDRESS_QUERY = "Fridon Khalvashi 2nd Deadlock, 5, Batumi";
const MAP_LINK = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
  ADDRESS_QUERY,
)}`;
const MAP_EMBED = `https://maps.google.com/maps?q=${encodeURIComponent(
  ADDRESS_QUERY,
)}&hl=en&z=12&output=embed`;
const WHATSAPP_NUMBER = "+995 599 87 57 73";
const WHATSAPP_LINK = "https://wa.me/995599875273";

export default function ContactsPage() {
  return (
    <div className="bg-[var(--cream)]">
      <section className="mx-auto max-w-[1100px] px-6 pt-16 pb-10 text-center md:pt-20 md:pb-12">
        <h1 className="text-2xl font-bold tracking-[0.06em] uppercase text-[var(--ink)] md:text-3xl">
          Pickup Location
        </h1>
        <p className="mx-auto mt-5 max-w-[640px] text-base leading-relaxed text-[var(--ink)] md:text-lg">
          We don&apos;t have dine-in service or a dessert display, but
          you&apos;re always welcome to pick up your order.
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
        <div className="grid gap-12 text-center md:grid-cols-3 md:gap-8">
          <InfoColumn
            icon={<Clock strokeWidth={1.4} className="h-12 w-12" />}
            title="Monday – Sunday"
          >
            <p>
              <span className="font-semibold">Store Hours:</span> 09:00 - 18:00
            </p>
            <p>
              <span className="font-semibold">Manager Hours:</span> 09:00 - 20:00
            </p>
          </InfoColumn>

          <InfoColumn
            icon={<MapPin strokeWidth={1.4} className="h-12 w-12" />}
            title="Address"
          >
            <p>Fridon Khalvashi 2nd Deadlock, 5</p>
            <p>Batumi, Georgia</p>
          </InfoColumn>

          <InfoColumn
            icon={<WhatsAppIcon className="h-12 w-12" />}
            title="Whats App"
          >
            <a
              href={WHATSAPP_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80"
            >
              {WHATSAPP_NUMBER}
            </a>
          </InfoColumn>
        </div>
      </section>
    </div>
  );
}

function InfoColumn({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-4 text-[var(--ink)]">
      <div className="text-[var(--ink)]/80">{icon}</div>
      <h2 className="text-lg font-bold tracking-[0.06em] uppercase md:text-xl">
        {title}
      </h2>
      <div className="space-y-1 text-sm md:text-base">{children}</div>
    </div>
  );
}

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      <path d="M8.5 9.5c0 3.5 3 6.5 6.5 6.5l1-1.5-2-1-1 1c-1.5-.5-2.5-1.5-3-3l1-1-1-2-1.5 1z" />
    </svg>
  );
}
