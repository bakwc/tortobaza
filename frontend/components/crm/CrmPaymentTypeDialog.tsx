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
  flowwow: "paymentFlowwow",
  crypto: "paymentCrypto",
  online: "paymentOnline",
} as const;

const PAYMENT_TYPES = [
  "unknown",
  "cash",
  "terminal",
  "tbc",
  "bog",
  "flowwow",
  "crypto",
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
      <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
          {t("paymentMethod")}
        </DialogTitle>
        <RadioGroup
          value={selected}
          onValueChange={(value) => setSelected(value as CrmOrderPaymentType)}
          className="mt-4 grid grid-cols-1 gap-2"
        >
          {PAYMENT_TYPES.map((type) => (
            <label
              key={type}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-2xl border px-3 py-3 text-sm",
                selected === type
                  ? "border-[var(--brand)] bg-[var(--cream)]"
                  : "border-[var(--line)]",
              )}
            >
              <RadioGroupItem value={type} />
              <span className="flex-1 font-medium text-[var(--ink)]">
                {t(PAYMENT_TYPE_MESSAGE_KEYS[type])}
              </span>
              {selected === type ? <Check className="h-4 w-4 text-[var(--brand)]" /> : null}
            </label>
          ))}
        </RadioGroup>
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
