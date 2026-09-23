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
    <span className="flex shrink-0 items-center gap-2">
      {tel ? (
        <a
          href={tel}
          className="text-[var(--brand)] hover:opacity-80"
          aria-label="Phone"
        >
          <Phone className="h-6 w-6" />
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
          <WhatsAppIcon className="h-6 w-6" />
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
          <TelegramIcon className="h-6 w-6" />
        </a>
      ) : null}
    </span>
  );
}

export function CrmPhoneList({ phones }: { phones: CrmPhone[] }) {
  return (
    <div className="flex flex-col gap-2">
      {phones.map((phone) => (
        <div key={phone.e164} className="flex items-center justify-between gap-3">
          <span className="min-w-0 font-medium">{phone.e164}</span>
          <CrmContactLinks tel={phone.tel} whatsapp={phone.whatsapp} telegram={phone.telegram} />
        </div>
      ))}
    </div>
  );
}
