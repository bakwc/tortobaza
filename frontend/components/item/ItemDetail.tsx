"use client";

import { useMemo, useState } from "react";
import { Minus, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
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

  const missingRequired = product.option_groups
    .filter((g) => g.is_required && (selection[g.id]?.length ?? 0) === 0)
    .map((g) => g.name);

  const handleAdd = async () => {
    setError(null);
    if (missingRequired.length > 0) {
      setError(`Please choose: ${missingRequired.join(", ")}`);
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
      const message = e instanceof Error ? e.message : "Failed to add item";
      setError(message);
    }
  };

  const images = product.images.length > 0 ? product.images : [];
  const heroImage = images[activeImage]?.image ?? null;

  return (
    <div
      className={cn(
        "grid h-full min-h-0 gap-0 bg-white md:grid-cols-2",
        variant === "modal" && "max-h-[calc(100vh-1.5rem)]",
      )}
    >
      <div className="bg-[var(--cream)] p-4 md:p-6">
        <div className="flex h-full flex-col gap-3">
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
                No image
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
        <div className="flex-1 overflow-y-auto px-6 pb-32 pt-6 md:px-8">
          <h1 className="font-display text-3xl text-[var(--ink)] md:text-4xl">
            {product.name}
          </h1>
          {product.description ? (
            <p className="mt-3 text-sm leading-relaxed text-[var(--ink)]/70">
              {product.description}
            </p>
          ) : null}

          <div className="mt-8 space-y-8">
            {product.option_groups.map((group) => (
              <OptionGroup
                key={group.id}
                group={group}
                selected={selection[group.id] ?? []}
                onChange={(next) =>
                  setSelection((prev) => ({ ...prev, [group.id]: next }))
                }
              />
            ))}
          </div>

          <div className="mt-8">
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Notes"
              rows={3}
            />
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-0 border-t border-[var(--line)] bg-white/95 px-6 py-4 backdrop-blur md:px-8">
          {error ? (
            <p className="mb-2 text-xs text-[var(--danger)]">{error}</p>
          ) : null}
          <div className="flex items-center gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] p-1">
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                aria-label="Decrease"
                className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-[var(--cream)]"
              >
                <Minus className="h-4 w-4" />
              </button>
              <span className="min-w-[2ch] text-center tabular-nums">{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((q) => q + 1)}
                aria-label="Increase"
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
              Add for {formatAed(lineTotal)}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
