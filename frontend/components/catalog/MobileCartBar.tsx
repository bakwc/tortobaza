"use client";

import { useTranslations } from "next-intl";
import { ShoppingBag } from "lucide-react";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";
import { useCart } from "@/hooks/useCart";
import { formatAed } from "@/lib/format";
import { CartEditor } from "@/components/catalog/CartEditor";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function MobileCartBar() {
  const t = useTranslations("catalog");
  const { data: cart } = useCart();
  const items = cart?.items ?? [];
  const count = items.reduce((sum, i) => sum + i.quantity, 0);

  if (count === 0) return null;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center justify-between rounded-full bg-[var(--brand)] px-5 py-3 text-[var(--brand-foreground)] shadow-lg"
        >
          <span className="inline-flex items-center gap-2 text-sm font-medium">
            <span className="relative inline-flex">
              <ShoppingBag className="h-5 w-5" />
              <span className="absolute -right-2 -top-2 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-white px-1 text-[10px] font-semibold text-[var(--brand)]">
                {count}
              </span>
            </span>
            {t("viewOrder")}
          </span>
          <span className="text-sm font-medium">{formatAed(cart?.subtotal ?? "0")}</span>
        </button>
      </DialogTrigger>
      <DialogContent className="bottom-0 left-0 top-auto flex w-full max-h-[85vh] translate-x-0 translate-y-0 flex-col rounded-b-none rounded-t-3xl p-6 pt-14">
        <VisuallyHidden.Root asChild>
          <DialogTitle>{t("yourOrder")}</DialogTitle>
        </VisuallyHidden.Root>
        <CartEditor />
      </DialogContent>
    </Dialog>
  );
}
