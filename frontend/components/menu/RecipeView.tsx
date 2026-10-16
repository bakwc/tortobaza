"use client";

import { useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { BookOpen, Layers, Pencil, TriangleAlert, ZoomIn } from "lucide-react";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { Button } from "@/components/ui/button";
import { DialogTitle } from "@/components/ui/dialog";
import { formatQuantity } from "@/components/menu/ui";
import type { MenuImage, RecipeLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function PanelChip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/80",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function RecipePanel({
  marker,
  title,
  aside,
  children,
}: {
  marker: ReactNode;
  title: string;
  aside: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
      <div className="flex flex-wrap items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--brand)]/15 text-sm font-bold text-[var(--brand)]">
          {marker}
        </span>
        <h3 className="min-w-0 flex-1 text-sm font-semibold text-[var(--ink)]">{title}</h3>
        <div className="flex flex-wrap items-center gap-1.5">{aside}</div>
      </div>
      {children}
    </section>
  );
}

export function RecipeRow({
  name,
  tag,
  amount,
  loss,
  warning,
}: {
  name: string;
  tag: string | null;
  amount: string;
  loss: string | null;
  warning: boolean;
}) {
  const t = useTranslations("stock");
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-[var(--cream-soft)]">
      <span className="flex min-w-0 flex-1 flex-wrap items-center gap-2 text-[var(--ink)]">
        <span className="font-medium">{name}</span>
        {tag !== null ? (
          <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-900">
            {tag}
          </span>
        ) : null}
        {warning ? (
          <TriangleAlert className="h-3.5 w-3.5 text-amber-600" aria-label={t("missingCompositionsTitle")} />
        ) : null}
      </span>
      {loss !== null ? (
        <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
          {t("lossPercent")} {loss}%
        </span>
      ) : null}
      <span className="shrink-0 text-right font-semibold tabular-nums text-[var(--ink)]">{amount}</span>
    </div>
  );
}

export function CompositionList({ lines }: { lines: RecipeLine[] }) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  if (lines.length === 0) {
    return <p className="px-4 py-3 text-sm text-[var(--muted-2)]">—</p>;
  }
  return (
    <div className="divide-y divide-[var(--line)]">
      {lines.map((line) => {
        const loss = formatQuantity(line.loss_percent);
        return (
          <RecipeRow
            key={line.id}
            name={line.name}
            tag={line.semi_product !== null ? t("semiProduct") : null}
            amount={`${formatQuantity(line.quantity)} ${units(line.unit)}`}
            loss={loss === "0" ? null : loss}
            warning={false}
          />
        );
      })}
    </div>
  );
}

export function RecipeView({
  title,
  badges,
  stats,
  images,
  compositionTitle,
  lines,
  sections,
  method,
  onEdit,
  children,
}: {
  title: string;
  badges: string[];
  stats: { label: string; value: string }[];
  images: MenuImage[];
  compositionTitle: string;
  lines: RecipeLine[];
  sections: { name: string; method: string; lines: RecipeLine[] }[];
  method: string;
  onEdit: () => void;
  children: ReactNode;
}) {
  const t = useTranslations("stock");
  const [active, setActive] = useState(0);
  const image = images.length === 0 ? null : images[Math.min(active, images.length - 1)];
  return (
    <div className="grid gap-5">
      <div className={cn("grid gap-5", image && "md:grid-cols-12")}>
        {image ? (
          <div className="grid content-start gap-2 md:col-span-5">
            <a
              href={image.image.src}
              target="_blank"
              rel="noreferrer"
              className="group relative block aspect-square overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--cream)]"
            >
              <img
                src={image.image.src}
                srcSet={image.image.srcset}
                sizes="(max-width: 768px) 90vw, 360px"
                alt=""
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
              />
              <span className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                <ZoomIn className="h-4 w-4" />
              </span>
            </a>
            {images.length > 1 ? (
              <div className="flex flex-wrap gap-2">
                {images.map((row, index) => (
                  <button
                    key={row.id}
                    type="button"
                    onClick={() => setActive(index)}
                    className={cn(
                      "h-14 w-14 shrink-0 overflow-hidden rounded-xl border-2 bg-[var(--cream)] transition-all",
                      row.id === image.id
                        ? "border-[var(--brand)] ring-2 ring-[var(--brand)]/30"
                        : "border-[var(--line)] opacity-70 hover:opacity-100",
                    )}
                  >
                    <img src={row.image.src} srcSet={row.image.srcset} sizes="56px" alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className={cn("flex flex-col gap-4", image && "md:col-span-7")}>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--line)] pb-4 pr-10">
            <div className="grid min-w-0 gap-2">
              <DialogTitle className="text-2xl font-semibold leading-tight text-[var(--ink)]">{title}</DialogTitle>
              {badges.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {badges.map((badge) => (
                    <span
                      key={badge}
                      className="rounded-full bg-[var(--brand)]/15 px-3 py-1 text-xs font-semibold text-[var(--brand)]"
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
          {stats.length > 0 ? (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {stats.map((stat) => (
                <div key={stat.label} className="rounded-2xl border border-[var(--line)] bg-[var(--cream-soft)] p-3">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted-2)] lg:text-xs">
                    {stat.label}
                  </span>
                  <p className="mt-1 text-base font-bold tabular-nums text-[var(--ink)]">{stat.value}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {lines.length > 0 || sections.length === 0 ? (
        <RecipePanel
          marker={<Layers className="h-4 w-4" />}
          title={compositionTitle}
          aside={<PanelChip>{lines.length}</PanelChip>}
        >
          <CompositionList lines={lines} />
        </RecipePanel>
      ) : null}

      {sections.map((section, index) => (
        <RecipePanel
          key={section.name}
          marker={index + 1}
          title={section.name}
          aside={<PanelChip>{t("componentsCount", { count: section.lines.length })}</PanelChip>}
        >
          <CompositionList lines={section.lines} />
          {section.method.trim() ? (
            <div className="border-t border-[var(--line)] bg-[var(--cream-soft)]/60 px-4 py-3">
              <MarkdownView value={section.method} />
            </div>
          ) : null}
        </RecipePanel>
      ))}

      {children}

      {method.trim() || sections.length === 0 ? (
        <RecipePanel marker={<BookOpen className="h-4 w-4" />} title={t("method")} aside={null}>
          <div className="px-4 py-4">
            {method.trim() ? (
              <MarkdownView value={method} />
            ) : (
              <p className="text-sm text-[var(--muted-2)]">{t("noMethod")}</p>
            )}
          </div>
        </RecipePanel>
      ) : null}
    </div>
  );
}
