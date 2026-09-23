"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, History, MoreHorizontal, Trash2, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CrmOrderHistoryDialog } from "@/components/crm/CrmOrderHistoryDialog";
import { Link } from "@/i18n/navigation";

export function CrmOrderActionsMenu({
  orderId,
  clientToken,
  onDelete,
}: {
  orderId: number;
  clientToken: string | null;
  onDelete: (() => void) | null;
}) {
  const t = useTranslations("crm");
  const [open, setOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

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
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => {
              setOpen(false);
              setHistoryOpen(true);
            }}
          >
            <History className="h-4 w-4" />
            {t("history")}
          </button>
          {clientToken ? (
            <Link
              href={`/crm/client/${clientToken}`}
              target="_blank"
              rel="noreferrer"
              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
              onClick={() => setOpen(false)}
            >
              <Link2 className="h-4 w-4" />
              {t("clientLink")}
            </Link>
          ) : null}
          <Link
            href={`/crm/${orderId}/invoice`}
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => setOpen(false)}
          >
            <FileText className="h-4 w-4" />
            {t("invoice")}
          </Link>
          {onDelete ? (
            <button
              type="button"
              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--danger)] hover:bg-red-50"
              onClick={() => {
                setOpen(false);
                onDelete();
              }}
            >
              <Trash2 className="h-4 w-4" />
              {t("deleteOrder")}
            </button>
          ) : null}
        </div>
      ) : null}
      <CrmOrderHistoryDialog
        orderId={orderId}
        open={historyOpen}
        onOpenChange={setHistoryOpen}
      />
    </div>
  );
}
