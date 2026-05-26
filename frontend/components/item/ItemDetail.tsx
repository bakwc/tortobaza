"use client";

import { useMemo, useState } from "react";
import { Minus, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { OptionGroup, type OptionSelection } from "./OptionGroup";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { formatAed } from "@/lib/format";
import { useAddCartItem } from "@/hooks/useCart";
import type { ProductDetail } from "@/lib/api/types";

export function ItemDetail({
  product,
  variant = "page",
  onAdded,
}: {
  product: ProductDetail;
  variant?: "page" | "modal";
  onAdded?: () => void;
}) {
  const t = useTranslations("item");
  const router = useRouter();
  const addItem = useAddCartItem();

  const [activeImage, setActiveImage] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [selection, setSelection] = useState<OptionSelection>(() => {
    const initial: OptionSelection = {};
    for (const group of product.option_groups) {
      initial[group.id] = [];
    }
    return initial;
  });

  const unitPrice = useMemo(() => {
    let total = Number.parseFloat(product.base_price);
    for (const group of product.option_groups) {
      const selectedIds = selection[group.id] ?? [];
      for (const optionId of selectedIds) {
        const option = group.options.find((o) => o.id === optionId);
        if (option) total += Number.parseFloat(option.price_delta);
      }
    }
    return total;
  }, [product, selection]);

  const lineTotal = unitPrice * quantity;

  const invalidGroups = product.option_groups
    .filter((g) => {
      const count = selection[g.id]?.length ?? 0;
      if (count < g.min_selections) return true;
      if (g.max_selections !== null && count > g.max_selections) return true;
      return false;
    })
    .map((g) => g.name);

  const handleAdd = async () => {
    setError(null);
    if (invalidGroups.length > 0) {
      setError(`${t("pleaseChoosePrefix")} ${invalidGroups.join(", ")}`);
      return;
    }
    const optionIds = Object.values(selection).flat();
    try {
      await addItem.mutateAsync({
        product_id: product.id,
        quantity,
        option_ids: optionIds,
        comment,
      });
      if (onAdded) onAdded();
      else router.back();
    } catch (e) {
      const message = e instanceof Error ? e.message : t("failedAdd");
      setError(message);
    }
  };

  const images = product.images.length > 0 ? product.images : [];
  const heroImage = images[activeImage]?.image ?? null;

  return (
    <div
      className={cn(
        "grid min-h-0 gap-0 bg-white md:grid-cols-2 md:grid-rows-1",
        variant === "page" &&
          "h-[calc(100dvh-9rem)] overflow-y-auto md:overflow-hidden",
        variant === "modal" &&
          "h-full max-h-[calc(100vh-1.5rem)] overflow-y-auto md:overflow-hidden",
      )}
    >
      <div className="min-h-0 bg-white p-4 md:p-6">
        <div className="flex h-full min-h-0 flex-col gap-3">
          <div className="aspect-square w-full overflow-hidden rounded-3xl bg-white">
            {heroImage ? (
              <img
                src={heroImage.src}
                srcSet={heroImage.srcset}
                sizes="(min-width: 768px) min(50vw, 560px), 100vw"
                alt={product.name}
                className="h-full w-full object-cover"
                decoding="async"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-[var(--muted-2)]">
                {t("noImage")}
              </div>
            )}
          </div>
          {images.length > 1 ? (
            <div className="scrollbar-none flex gap-3 overflow-x-auto">
              {images.map((img, i) => (
                <button
                  key={img.id}
                  type="button"
                  onClick={() => setActiveImage(i)}
                  className={cn(
                    "h-20 w-20 shrink-0 overflow-hidden rounded-2xl ring-1 transition",
                    i === activeImage
                      ? "ring-2 ring-[var(--brand)]"
                      : "ring-[var(--line)] hover:ring-[var(--muted-2)]",
                  )}
                >
                  <img
                    src={img.image.src}
                    srcSet={img.image.srcset}
                    sizes="80px"
                    alt={img.alt ?? `${product.name} ${i + 1}`}
                    className="h-full w-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      <div className="relative flex min-h-0 flex-col">
        <div className="min-h-0 flex-1 px-6 pt-6 md:overflow-y-auto md:px-8 md:pb-32">
          <h1 className="font-display text-3xl text-[var(--ink)] md:text-4xl">{product.name}</h1>
          {product.description ? (
            <p className="mt-3 text-sm leading-relaxed text-[var(--ink)]/70">{product.description}</p>
          ) : null}

          <div className="mt-8 space-y-8">
            {product.option_groups.map((group) => (
              <OptionGroup
                key={group.id}
                group={group}
                selected={selection[group.id] ?? []}
                onChange={(next) => setSelection((prev) => ({ ...prev, [group.id]: next }))}
              />
            ))}
          </div>

          <div className="mt-8">
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t("notesPlaceholder")}
              rows={3}
            />
          </div>
        </div>

        <div className="border-t border-[var(--line)] bg-white/95 px-6 py-4 backdrop-blur md:absolute md:inset-x-0 md:bottom-0 md:px-8">
          {error ? <p className="mb-2 text-xs text-[var(--danger)]">{error}</p> : null}
          <div className="flex items-center gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] p-1">
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                aria-label={t("decreaseAria")}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-[var(--cream)]"
              >
                <Minus className="h-4 w-4" />
              </button>
              <span className="min-w-[2ch] text-center tabular-nums">{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((q) => q + 1)}
                aria-label={t("increaseAria")}
                className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-[var(--cream)]"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
            <Button
              type="button"
              variant="price"
              size="lg"
              onClick={handleAdd}
              disabled={addItem.isPending}
              className="flex-1"
            >
              {addItem.isPending ? <Spinner className="mr-2" /> : null}
              {t("addFor", { price: formatAed(lineTotal) })}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
