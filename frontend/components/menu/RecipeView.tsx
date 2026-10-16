"use client";

import { Fragment, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Pencil, TriangleAlert } from "lucide-react";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { Button } from "@/components/ui/button";
import { DialogTitle } from "@/components/ui/dialog";
import { formatQuantity } from "@/components/menu/ui";
import type { MenuImage, RecipeLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export type RecipeTableRow = {
  key: string;
  name: string;
  tag: string | null;
  amount: string;
  loss: string;
  warning: boolean;
};

export function RecipeHeading({ number, title, note }: { number: number | null; title: string; note: string }) {
  return (
    <div className="flex items-baseline gap-2 border-b border-[var(--line)] pb-2">
      {number !== null ? <span className="text-base font-semibold text-[var(--brand)]">{number}.</span> : null}
      <h3 className="text-base font-semibold text-[var(--ink)]">{title}</h3>
      {note ? <span className="text-sm text-[var(--muted-2)]">{note}</span> : null}
    </div>
  );
}

export function RecipeTable({ rows }: { rows: RecipeTableRow[] }) {
  const t = useTranslations("stock");
  if (rows.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
          <tr>
            <th className="py-1.5 pr-3 font-medium">{t("name")}</th>
            <th className="py-1.5 pr-3 text-right font-medium">{t("quantity")}</th>
            <th className="w-20 py-1.5 text-right font-medium">{t("lossPercent")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t border-[var(--line)]/70">
              <td className="py-2 pr-3 text-[var(--ink)]">
                <span className="inline-flex flex-wrap items-center gap-2">
                  {row.name}
                  {row.tag !== null ? (
                    <span className="text-xs italic text-[var(--muted-2)]">{row.tag}</span>
                  ) : null}
                  {row.warning ? (
                    <TriangleAlert className="h-3.5 w-3.5 text-amber-600" aria-label={t("missingCompositionsTitle")} />
                  ) : null}
                </span>
              </td>
              <td className="whitespace-nowrap py-2 pr-3 text-right font-medium tabular-nums text-[var(--ink)]">
                {row.amount}
              </td>
              <td className="whitespace-nowrap py-2 text-right tabular-nums text-[var(--muted-2)]">{row.loss}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CompositionTable({ lines }: { lines: RecipeLine[] }) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  return (
    <RecipeTable
      rows={lines.map((line) => {
        const loss = formatQuantity(line.loss_percent);
        return {
          key: String(line.id),
          name: line.name,
          tag: line.semi_product !== null ? t("semiProduct").toLowerCase() : null,
          amount: `${formatQuantity(line.quantity)} ${units(line.unit)}`,
          loss: loss === "0" ? "—" : `${loss}%`,
          warning: false,
        };
      })}
    />
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
    <div className="grid gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3 pr-10">
        <div className="grid min-w-0 gap-1.5">
          <DialogTitle className="text-2xl font-semibold leading-tight text-[var(--ink)]">{title}</DialogTitle>
          {badges.length > 0 ? (
            <p className="text-sm text-[var(--muted-2)]">
              {badges.map((badge, index) => (
                <Fragment key={badge}>
                  {index > 0 ? <span className="mx-1.5">·</span> : null}
                  {badge}
                </Fragment>
              ))}
            </p>
          ) : null}
          {stats.length > 0 ? (
            <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm">
              {stats.map((stat) => (
                <div key={stat.label} className="flex items-baseline gap-1.5">
                  <dt className="text-[var(--muted-2)]">{stat.label}:</dt>
                  <dd className="font-semibold tabular-nums text-[var(--ink)]">{stat.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
        <Button type="button" size="sm" variant="outline" onClick={onEdit}>
          <Pencil className="mr-1 h-4 w-4" />
          {t("edit")}
        </Button>
      </div>

      {image ? (
        <div className="grid gap-3">
          <a href={image.image.src} target="_blank" rel="noreferrer" className="block">
            <img src={image.image.src} alt="" className="max-h-72 w-full rounded-2xl bg-[var(--cream)] object-contain" />
          </a>
          {images.length > 1 ? (
            <div className="flex gap-2 overflow-x-auto">
              {images.map((row, index) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setActive(index)}
                  className={cn(
                    "shrink-0 overflow-hidden rounded-xl border-2",
                    row.id === image.id ? "border-[var(--brand)]" : "border-transparent opacity-70 hover:opacity-100",
                  )}
                >
                  <img src={row.image.src} alt="" className="h-16 w-16 object-cover" />
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {lines.length > 0 || sections.length === 0 ? (
        <div className="grid gap-2">
          <RecipeHeading number={null} title={compositionTitle} note="" />
          <CompositionTable lines={lines} />
        </div>
      ) : null}

      {sections.map((section, index) => (
        <div key={section.name} className="grid gap-2">
          <RecipeHeading number={index + 1} title={section.name} note="" />
          <CompositionTable lines={section.lines} />
          {section.method.trim() ? (
            <div className="mt-1">
              <MarkdownView value={section.method} />
            </div>
          ) : null}
        </div>
      ))}

      {children}

      {method.trim() || sections.length === 0 ? (
        <div className="grid gap-2">
          <RecipeHeading number={null} title={t("method")} note="" />
          {method.trim() ? (
            <MarkdownView value={method} />
          ) : (
            <p className="text-sm text-[var(--muted-2)]">{t("noMethod")}</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
