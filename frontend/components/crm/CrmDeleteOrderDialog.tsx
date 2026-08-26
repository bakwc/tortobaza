"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";

export function CrmDeleteOrderDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
  isError,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations("crm");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
          {t("deleteConfirmTitle")}
        </DialogTitle>
        <DialogDescription className="mt-2 text-sm text-[var(--muted-2)]">
          {t("deleteConfirmBody")}
        </DialogDescription>
        {isError ? (
          <p className="mt-3 text-sm text-[var(--danger)]">{t("deleteError")}</p>
        ) : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            {t("cancel")}
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="bg-[var(--danger)] text-white hover:bg-[var(--danger)]/90"
          >
            {isPending ? <Spinner className="h-4 w-4" /> : t("confirmDelete")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
