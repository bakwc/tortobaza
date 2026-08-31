"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";

export function CrmOrderActionsMenu({ orderId }: { orderId: number }) {
  const t = useTranslations("crm");
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 w-8 shrink-0 px-0"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={t("invoiceMenu")}
        aria-expanded={open}
      >
        <MoreHorizontal className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 min-w-[180px] rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg">
          <Link
            href={`/crm/${orderId}/invoice`}
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => setOpen(false)}
          >
            <FileText className="h-4 w-4" />
            {t("invoice")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
