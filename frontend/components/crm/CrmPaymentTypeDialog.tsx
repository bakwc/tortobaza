"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Spinner } from "@/components/ui/spinner";
import type { CrmOrderPaymentType } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const PAYMENT_TYPE_MESSAGE_KEYS = {
  unknown: "paymentUnknown",
  cash: "paymentCash",
  terminal: "paymentTerminal",
  tbc: "paymentTbc",
  bog: "paymentBog",
  tbank: "paymentTbank",
  flowwow: "paymentFlowwow",
  crypto: "paymentCrypto",
  paypal: "paymentPaypal",
  online: "paymentOnline",
} as const;

const PAYMENT_TYPES = [
  "unknown",
  "cash",
  "terminal",
  "tbc",
  "bog",
  "tbank",
  "flowwow",
  "crypto",
  "paypal",
  "online",
] as const satisfies CrmOrderPaymentType[];

export function CrmPaymentTypeDialog({
  open,
  onOpenChange,
  paymentType,
  onConfirm,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  paymentType: CrmOrderPaymentType;
  onConfirm: (paymentType: CrmOrderPaymentType) => void;
  isPending: boolean;
}) {
  const t = useTranslations("crm");
  const [selected, setSelected] = useState<CrmOrderPaymentType>(paymentType);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-1.5rem)] w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] flex-col p-4 sm:p-6">
        <DialogTitle className="shrink-0 pr-10 text-lg font-semibold text-[var(--ink)]">
          {t("paymentMethod")}
        </DialogTitle>
        <RadioGroup
          value={selected}
          onValueChange={(value) => setSelected(value as CrmOrderPaymentType)}
          className="-mx-1 mt-4 grid min-h-0 flex-1 grid-cols-2 content-start gap-2 overflow-y-auto overscroll-contain px-1 py-1"
        >
          {PAYMENT_TYPES.map((type) => (
            <label
              key={type}
              className={cn(
                "flex min-w-0 cursor-pointer items-center gap-2 rounded-2xl border px-3 py-2 text-sm",
                selected === type
                  ? "border-[var(--brand)] bg-[var(--cream)]"
                  : "border-[var(--line)]",
              )}
            >
              <RadioGroupItem value={type} />
              <span className="min-w-0 flex-1 break-words leading-tight font-medium text-[var(--ink)]">
                {t(PAYMENT_TYPE_MESSAGE_KEYS[type])}
              </span>
              {selected === type ? <Check className="h-4 w-4 shrink-0 text-[var(--brand)]" /> : null}
            </label>
          ))}
        </RadioGroup>
        <div className="mt-4 flex shrink-0 justify-end gap-2 sm:mt-6">
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
            onClick={() => onConfirm(selected)}
            disabled={isPending}
          >
            {isPending ? <Spinner className="h-4 w-4" /> : t("markPaid")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
