"use client";

import { useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Pencil } from "lucide-react";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { Button } from "@/components/ui/button";
import { DialogTitle } from "@/components/ui/dialog";
import { CardTitle, formatQuantity } from "@/components/menu/ui";
import type { MenuImage, RecipeLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function CompositionTable({ lines }: { lines: RecipeLine[] }) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  if (lines.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
          <tr>
            <th className="py-2 pr-3 font-medium">{t("name")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("quantity")}</th>
            <th className="py-2 text-right font-medium">{t("lossPercent")}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr key={line.id} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3">
                <span className="inline-flex flex-wrap items-center gap-2">
                  {line.name}
                  {line.semi_product !== null ? (
                    <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-xs text-[var(--ink)]/70">
                      {t("semiProduct")}
                    </span>
                  ) : null}
                </span>
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {formatQuantity(line.quantity)} {units(line.unit)}
              </td>
              <td className="py-2 text-right tabular-nums">{formatQuantity(line.loss_percent)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RecipeView({
  title,
  badges,
  images,
  compositionTitle,
  lines,
  method,
  onEdit,
  children,
}: {
  title: string;
  badges: string[];
  images: MenuImage[];
  compositionTitle: string;
  lines: RecipeLine[];
  method: string;
  onEdit: () => void;
  children: ReactNode;
}) {
  const t = useTranslations("stock");
  const [active, setActive] = useState(0);
  const image = images.length === 0 ? null : images[Math.min(active, images.length - 1)];
  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3 pr-10">
        <div className="grid gap-2">
          <DialogTitle className="text-xl font-semibold text-[var(--ink)]">{title}</DialogTitle>
          {badges.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {badges.map((badge) => (
                <span
                  key={badge}
                  className="rounded-full border border-[var(--line)] bg-[var(--cream)] px-2.5 py-0.5 text-xs text-[var(--ink)]"
                >
                  {badge}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <Button type="button" size="sm" onClick={onEdit}>
          <Pencil className="mr-1 h-4 w-4" />
          {t("edit")}
        </Button>
      </div>

      {image ? (
        <div className="grid gap-3">
          <a href={image.image.src} target="_blank" rel="noreferrer" className="block">
            <img src={image.image.src} alt="" className="max-h-72 w-full rounded-2xl object-contain bg-[var(--cream)]" />
          </a>
          {images.length > 1 ? (
            <div className="flex gap-2 overflow-x-auto">
              {images.map((row, index) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setActive(index)}
                  className={cn(
                    "shrink-0 overflow-hidden rounded-xl border",
                    row.id === image.id ? "border-[var(--ink)]" : "border-transparent",
                  )}
                >
                  <img src={row.image.src} alt="" className="h-16 w-16 object-cover" />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-2">
        <CardTitle>{compositionTitle}</CardTitle>
        <CompositionTable lines={lines} />
      </div>

      {children}

      <div className="grid gap-2">
        <CardTitle>{t("method")}</CardTitle>
        {method.trim() ? (
          <MarkdownView value={method} />
        ) : (
          <p className="text-sm text-[var(--muted-2)]">{t("noMethod")}</p>
        )}
      </div>
    </div>
  );
}
