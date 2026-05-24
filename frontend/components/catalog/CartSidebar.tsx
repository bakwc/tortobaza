"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Minus, Plus, ShoppingBag, Trash2 } from "lucide-react";
import {
  useCart,
  useClearCart,
  useRemoveCartItem,
  useUpdateCartItem,
} from "@/hooks/useCart";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatAed } from "@/lib/format";
import { isMainSweetChillHost } from "@/lib/site-host";
import type { CartItem } from "@/lib/api/types";

export function CartSidebar() {
  const router = useRouter();
  const t = useTranslations("catalog");
  const { data: cart } = useCart();
  const clear = useClearCart();
  const remove = useRemoveCartItem();
  const update = useUpdateCartItem();
  const [notOpenDialogOpen, setNotOpenDialogOpen] = useState(false);

  const items = cart?.items ?? [];
  const isEmpty = items.length === 0;

  const handleConfirm = () => {
    const host =
      typeof window !== "undefined" ? window.location.hostname.toLowerCase() : "";
    if (isMainSweetChillHost(host)) {
      setNotOpenDialogOpen(true);
      return;
    }
    router.push("/checkout");
  };

  return (
    <aside className="sticky top-36 flex h-[calc(100vh-10rem)] flex-col bg-white p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-[22px] font-normal text-[#666]">{t("yourOrder")}</h2>
        {!isEmpty ? (
          <button
            type="button"
            onClick={() => clear.mutate()}
            disabled={clear.isPending}
            aria-label={t("clearCartAria")}
            className="rounded-full p-2 text-[var(--ink)]/60 hover:bg-[var(--cream)] hover:text-[var(--ink)] disabled:opacity-50"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        ) : null}
      </div>

      {isEmpty ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center text-[var(--ink)]/60">
          <ShoppingBag className="h-16 w-16 stroke-[1.2]" />
          <p className="text-sm">{t("basketEmpty")}</p>
        </div>
      ) : (
        <div className="mt-4 flex flex-1 flex-col gap-4 overflow-y-auto pr-1">
          {items.map((item) => (
            <CartLine
              key={item.id}
              item={item}
              onIncrement={() =>
                update.mutate({ id: item.id, body: { quantity: item.quantity + 1 } })
              }
              onDecrement={() => {
                if (item.quantity <= 1) {
                  remove.mutate(item.id);
                } else {
                  update.mutate({ id: item.id, body: { quantity: item.quantity - 1 } });
                }
              }}
              onRemove={() => remove.mutate(item.id)}
            />
          ))}
        </div>
      )}

      {!isEmpty ? (
        <div className="mt-4 border-t border-[var(--line)] pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--ink)]/60">{t("subtotal")}</span>
            <span className="font-medium">{formatAed(cart?.subtotal ?? "0")}</span>
          </div>
          <Button type="button" size="lg" className="mt-4 w-full" onClick={handleConfirm}>
            {t("confirm")}
          </Button>
        </div>
      ) : null}

      <Dialog open={notOpenDialogOpen} onOpenChange={setNotOpenDialogOpen}>
        <DialogContent className="max-w-lg gap-0 overflow-hidden border-0 p-0 sm:max-w-lg">
          <div className="bg-gradient-to-br from-[var(--brand)]/15 via-white to-[var(--cream)] px-8 pb-2 pt-10">
            <DialogTitle className="font-display text-center text-3xl leading-tight text-[var(--ink)]">
              {t("notReadyTitle")}
            </DialogTitle>
          </div>
          <div className="space-y-4 px-8 pb-8 pt-4">
            <DialogDescription className="text-center text-base leading-relaxed text-[var(--ink)]/80">
              {t("notReadyBody")}
            </DialogDescription>
            <Button
              type="button"
              size="lg"
              className="w-full"
              onClick={() => setNotOpenDialogOpen(false)}
            >
              {t("ok")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </aside>
  );
}

function CartLine({
  item,
  onIncrement,
  onDecrement,
  onRemove,
}: {
  item: CartItem;
  onIncrement: () => void;
  onDecrement: () => void;
  onRemove: () => void;
}) {
  const t = useTranslations("catalog");

  return (
    <div className="flex gap-3">
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-2xl bg-[var(--cream)]">
        {item.product.primary_image ? (
          <img
            src={item.product.primary_image.src}
            srcSet={item.product.primary_image.srcset}
            sizes="80px"
            alt={item.product.name}
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
          />
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-1 text-sm">
        <div className="flex items-start justify-between gap-2">
          <div className="font-medium leading-snug">{item.product.name}</div>
          <button
            type="button"
            onClick={onRemove}
            aria-label={t("removeAria")}
            className="text-[var(--ink)]/40 hover:text-[var(--danger)]"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
        {item.options.length > 0 ? (
          <ul className="space-y-0.5 text-xs text-[var(--ink)]/60">
            {item.options.map((opt) => (
              <li key={opt.id}>
                <span className="opacity-70">{opt.group_name}:</span> {opt.name}
              </li>
            ))}
          </ul>
        ) : null}
        {item.comment ? (
          <p className="text-xs italic text-[var(--ink)]/60">“{item.comment}”</p>
        ) : null}
        <div className="mt-1 flex items-center justify-between">
          <div className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] bg-[var(--cream-soft)] p-1">
            <button
              type="button"
              onClick={onDecrement}
              aria-label={t("decreaseAria")}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white text-[var(--ink)] hover:bg-[var(--cream)]"
            >
              <Minus className="h-3.5 w-3.5" />
            </button>
            <span className="min-w-[1.5rem] text-center text-sm tabular-nums">{item.quantity}</span>
            <button
              type="button"
              onClick={onIncrement}
              aria-label={t("increaseAria")}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-white text-[var(--ink)] hover:bg-[var(--cream)]"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <span className="font-medium">{formatAed(item.line_total)}</span>
        </div>
      </div>
    </div>
  );
}
