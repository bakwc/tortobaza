import { Phone } from "lucide-react";
import { TelegramIcon, WhatsAppIcon } from "@/content/contacts/icons";
import type { CrmOrder } from "@/lib/api/types";

type CrmPhone = CrmOrder["phones"][number];

type CrmContactLinksProps = {
  tel: string | null;
  whatsapp: string | null;
  telegram: string | null;
};

export function CrmContactLinks({ tel, whatsapp, telegram }: CrmContactLinksProps) {
  if (!tel && !whatsapp && !telegram) {
    return null;
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-1">
      {tel ? (
        <a
          href={tel}
          className="text-[var(--brand)] hover:opacity-80"
          aria-label="Phone"
        >
          <Phone className="h-4 w-4" />
        </a>
      ) : null}
      {whatsapp ? (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[var(--brand)] hover:opacity-80"
          aria-label="WhatsApp"
        >
          <WhatsAppIcon className="h-4 w-4" />
        </a>
      ) : null}
      {telegram ? (
        <a
          href={telegram}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[var(--brand)] hover:opacity-80"
          aria-label="Telegram"
        >
          <TelegramIcon className="h-4 w-4" />
        </a>
      ) : null}
    </span>
  );
}

export function CrmPhoneList({ phones }: { phones: CrmPhone[] }) {
  if (phones.length === 0) {
    return null;
  }
  return (
    <p className="mt-1 flex flex-wrap items-center gap-y-1 font-medium">
      {phones.map((phone, index) => (
        <span key={`${phone.e164}-${index}`} className="inline-flex items-center gap-1.5">
          {index > 0 ? <span className="mx-1.5">,</span> : null}
          <span>{phone.e164}</span>
          <CrmContactLinks tel={phone.tel} whatsapp={phone.whatsapp} telegram={phone.telegram} />
        </span>
      ))}
    </p>
  );
}
