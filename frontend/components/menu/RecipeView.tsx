"use client";

import { Fragment, useEffect, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Check, ChevronsUpDown, Copy, Link2, Pencil, Printer, TriangleAlert } from "lucide-react";
import {
  expandComposition,
  hasExpandableLines,
  type CompositionBlock,
  type TechCardLine,
} from "@/components/menu/expandComposition";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { Button } from "@/components/ui/button";
import { DialogTitle } from "@/components/ui/dialog";
import { formatLineAmount, formatLossLabel, formatMoney, gramTotal, QueryState } from "@/components/menu/ui";
import { getPathname, Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import type { MenuImage, SemiProduct, TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export type RecipeTableRow = {
  key: string;
  name: string;
  href: string | null;
  tag: string | null;
  amount: string;
  loss: string;
  cost: string | null;
  warning: boolean;
};

export function componentHref(ingredient: number | null, semiProduct: number | null): string | null {
  if (ingredient !== null) return `/menu/ingredients?ingredient=${ingredient}`;
  if (semiProduct !== null) return `/menu/semi-products?semi=${semiProduct}`;
  return null;
}

export function RecipeHeading({ number, title, note }: { number: number | null; title: string; note: string }) {
  return (
    <div className="flex items-baseline gap-2 border-b border-[var(--line)] pb-2">
      {number !== null ? <span className="text-base font-semibold text-[var(--brand)]">{number}.</span> : null}
      <h3 className="text-base font-semibold text-[var(--ink)]">{title}</h3>
      {note ? <span className="text-sm text-[var(--muted-2)]">{note}</span> : null}
    </div>
  );
}

export function RecipeTable({ rows, total }: { rows: RecipeTableRow[]; total: string | null }) {
  const t = useTranslations("stock");
  const showCost = rows.some((row) => row.cost !== null);
  const showLoss = rows.some((row) => row.loss !== "");
  if (rows.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
          <tr>
            <th className="py-1.5 pr-3 font-medium">{t("name")}</th>
            <th className="py-1.5 pr-3 text-right font-medium">{t("quantity")}</th>
            {showLoss ? <th className="py-1.5 pr-3 text-right font-medium">{t("lossPercent")}</th> : null}
            {showCost ? <th className="w-28 py-1.5 text-right font-medium">{t("recipeCost")}</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t border-[var(--line)]/70">
              <td className="py-2 pr-3 text-[var(--ink)]">
                <span className="inline-flex flex-wrap items-center gap-2">
                  {row.href !== null ? (
                    <Link href={row.href} className="text-[var(--ink)] hover:text-[var(--brand)]">
                      {row.name}
                    </Link>
                  ) : (
                    row.name
                  )}
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
              {showLoss ? (
                <td className="whitespace-nowrap py-2 pr-3 text-right tabular-nums text-[var(--muted-2)]">{row.loss}</td>
              ) : null}
              {showCost ? (
                <td className="whitespace-nowrap py-2 text-right font-medium tabular-nums text-[var(--ink)]">
                  {row.cost ?? "—"}
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
        {total !== null ? (
          <tfoot>
            <tr className="border-t border-[var(--line)]">
              <td className="py-2 pr-3 font-medium text-[var(--ink)]">{t("total")}</td>
              <td className="whitespace-nowrap py-2 pr-3 text-right font-medium tabular-nums text-[var(--ink)]">
                {total}
              </td>
              {showLoss ? <td /> : null}
              {showCost ? <td /> : null}
            </tr>
          </tfoot>
        ) : null}
      </table>
    </div>
  );
}

function CompositionBlocks({
  blocks,
  gramsPerUnit,
}: {
  blocks: CompositionBlock[];
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  const units = useTranslations("stock.units");
  return (
    <div className="grid gap-4">
      {blocks.map((block) =>
        block.kind === "lines" ? (
          <CompositionTable key={block.key} lines={block.lines} gramsPerUnit={gramsPerUnit} />
        ) : (
          <div key={block.key} className="grid gap-2" style={{ marginLeft: block.depth * 16 }}>
            <RecipeHeading
              number={null}
              title={block.title}
              note={
                block.quantity === null || block.quantityUnit === null
                  ? ""
                  : formatLineAmount(block.quantity, units(block.quantityUnit))
              }
            />
            <CompositionBlocks blocks={block.blocks} gramsPerUnit={gramsPerUnit} />
            {block.method.trim() ? (
              <div className="mt-1">
                <MarkdownView value={block.method} />
              </div>
            ) : null}
          </div>
        ),
      )}
    </div>
  );
}

function CollapsedComposition({
  compositionTitle,
  lines,
  sections,
  gramsPerUnit,
}: {
  compositionTitle: string;
  lines: TechCardLine[];
  sections: { name: string; method: string; lines: TechCardLine[] }[];
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  return (
    <>
      {lines.length > 0 || sections.length === 0 ? (
        <div className="grid gap-2">
          <RecipeHeading number={null} title={compositionTitle} note="" />
          <CompositionTable lines={lines} gramsPerUnit={gramsPerUnit} />
        </div>
      ) : null}
      {sections.map((section, index) => (
        <div key={section.name} className="grid gap-2">
          <RecipeHeading number={index + 1} title={section.name} note="" />
          <CompositionTable lines={section.lines} gramsPerUnit={gramsPerUnit} />
          {section.method.trim() ? (
            <div className="mt-1">
              <MarkdownView value={section.method} />
            </div>
          ) : null}
        </div>
      ))}
    </>
  );
}

function ExpandedComposition({
  compositionTitle,
  lines,
  sections,
  techCards,
  semiProducts,
  gramsPerUnit,
}: {
  compositionTitle: string;
  lines: TechCardLine[];
  sections: { name: string; method: string; lines: TechCardLine[] }[];
  techCards: TechCard[];
  semiProducts: SemiProduct[];
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  return (
    <>
      {lines.length > 0 || sections.length === 0 ? (
        <div className="grid gap-2">
          <RecipeHeading number={null} title={compositionTitle} note="" />
          <CompositionBlocks
            blocks={expandComposition(lines, techCards, semiProducts, 0)}
            gramsPerUnit={gramsPerUnit}
          />
        </div>
      ) : null}
      {sections.map((section, index) => (
        <div key={section.name} className="grid gap-2">
          <RecipeHeading number={index + 1} title={section.name} note="" />
          <CompositionBlocks
            blocks={expandComposition(section.lines, techCards, semiProducts, 1)}
            gramsPerUnit={gramsPerUnit}
          />
          {section.method.trim() ? (
            <div className="mt-1">
              <MarkdownView value={section.method} />
            </div>
          ) : null}
        </div>
      ))}
    </>
  );
}

export function CompositionTable({
  lines,
  gramsPerUnit,
}: {
  lines: TechCardLine[];
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const total = formatLineAmount(
    String(
      gramTotal(
        lines.map((line) => ({
          quantity: line.quantity,
          quantity_unit: line.quantity_unit,
          grams_per_unit: line.ingredient === null ? null : gramsPerUnit(line.ingredient),
        })),
      ),
    ),
    units("g"),
  );
  return (
    <RecipeTable
      total={total}
      rows={lines.map((line) => {
        return {
          key: String(line.id),
          name: line.name,
          href:
            line.nested_section !== null
              ? null
              : line.nested_tech_card !== null
                ? `/menu?card=${line.nested_tech_card}`
                : componentHref(line.ingredient, line.semi_product),
          tag:
            line.nested_section !== null
              ? t("section")
              : line.nested_tech_card !== null
                ? t("techCard")
                : line.semi_product !== null
                  ? t("semiProduct").toLowerCase()
                  : null,
          amount: formatLineAmount(line.quantity, units(line.quantity_unit)),
          loss: formatLossLabel(line.quantity, line.loss_quantity, units(line.quantity_unit)),
          cost: line.cost === undefined ? null : formatMoney(line.cost),
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
  gramsPerUnit,
  method,
  onEdit,
  onClone,
  printHref,
  copyPath,
  semiProducts,
  children,
}: {
  title: string;
  badges: string[];
  stats: { label: string; value: string }[];
  images: MenuImage[];
  compositionTitle: string;
  lines: TechCardLine[];
  sections: { name: string; method: string; lines: TechCardLine[] }[];
  gramsPerUnit: (ingredientId: number) => string | null;
  method: string;
  onEdit: () => void;
  onClone: (() => void) | null;
  printHref: string | null;
  copyPath: string | null;
  semiProducts: SemiProduct[];
  children: ReactNode;
}) {
  const t = useTranslations("stock");
  const locale = useLocale();
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const techCards = useQuery({
    queryKey: ["menu", "tech-cards"],
    queryFn: () => api.menuTechCards.list(),
    enabled: expanded,
  });
  const canExpand = hasExpandableLines(lines, sections);
  const href = printHref === null ? null : expanded ? `${printHref}?expanded=1` : printHref;
  const image = images.length === 0 ? null : images[Math.min(active, images.length - 1)];
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const copyLink = () => {
    if (copyPath === null) return;
    const path = getPathname({ locale, href: copyPath });
    void navigator.clipboard.writeText(`${window.location.origin}${path}`);
    setCopied(true);
  };
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
        <div className="flex shrink-0 flex-wrap gap-2">
          {copyPath !== null ? (
            <Button type="button" size="sm" variant="outline" onClick={copyLink}>
              {copied ? <Check className="mr-1 h-4 w-4" /> : <Link2 className="mr-1 h-4 w-4" />}
              {copied ? t("linkCopied") : t("copyLink")}
            </Button>
          ) : null}
          {canExpand ? (
            <Button type="button" size="sm" variant="outline" onClick={() => setExpanded((value) => !value)}>
              <ChevronsUpDown className="mr-1 h-4 w-4" />
              {expanded ? t("collapseComposition") : t("expandComposition")}
            </Button>
          ) : null}
          {href !== null ? (
            <Button size="sm" variant="outline" asChild>
              <Link href={href} target="_blank" rel="noreferrer">
                <Printer className="mr-1 h-4 w-4" />
                {t("print")}
              </Link>
            </Button>
          ) : null}
          <Button type="button" size="sm" variant="outline" onClick={onEdit}>
            <Pencil className="mr-1 h-4 w-4" />
            {t("edit")}
          </Button>
          {onClone !== null ? (
            <Button type="button" size="sm" variant="outline" onClick={onClone}>
              <Copy className="mr-1 h-4 w-4" />
              {t("clone")}
            </Button>
          ) : null}
        </div>
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

      {expanded ? (
        <QueryState isLoading={techCards.data === undefined} isError={techCards.isError}>
          <ExpandedComposition
            compositionTitle={compositionTitle}
            lines={lines}
            sections={sections}
            techCards={techCards.data ?? []}
            semiProducts={semiProducts}
            gramsPerUnit={gramsPerUnit}
          />
        </QueryState>
      ) : (
        <CollapsedComposition
          compositionTitle={compositionTitle}
          lines={lines}
          sections={sections}
          gramsPerUnit={gramsPerUnit}
        />
      )}

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
