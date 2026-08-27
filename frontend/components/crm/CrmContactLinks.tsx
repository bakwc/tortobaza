import { Phone } from "lucide-react";
import { TelegramIcon, WhatsAppIcon } from "@/content/contacts/icons";

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
    <span className="flex shrink-0 items-center gap-1.5">
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
