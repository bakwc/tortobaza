"use client";

import { useTranslations } from "next-intl";
import { expandRecipe, type ExpandedRecipe, type TechCardLine } from "@/components/menu/expandComposition";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { formatShelfLife } from "@/components/menu/shelfLife";
import { Button } from "@/components/ui/button";
import { formatLineAmount } from "@/components/menu/ui";
import type { SemiProduct, TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type PrintChapter = {
  key: string;
  name: string | null;
  lines: TechCard["lines"];
  method: string;
};

function titledMethod(method: string, fallbackName: string): PrintChapter | null {
  const trimmed = method.trim();
  if (!trimmed) return null;
  const match = /^(#{2,3}) (.+)\n([\s\S]*)$/.exec(trimmed);
  if (match === null) return { key: "card-method", name: fallbackName, lines: [], method: trimmed };
  return { key: "card-method", name: match[2].trim(), lines: [], method: match[3].trim() };
}

function printChapters(card: TechCard, methodLabel: string): PrintChapter[] {
  if (card.sections.length === 0) {
    return [{ key: "base", name: null, lines: card.lines, method: card.method }];
  }
  const chapters: PrintChapter[] = [];
  if (card.lines.length > 0) {
    chapters.push({ key: "base", name: null, lines: card.lines, method: "" });
  }
  for (const section of card.sections) {
    chapters.push({
      key: `section-${section.id}`,
      name: section.name,
      lines: section.lines,
      method: section.method,
    });
  }
  const tail = titledMethod(card.method, methodLabel);
  if (tail !== null) chapters.push(tail);
  return chapters;
}

function IngredientCell({ name, lines }: { name: string | null; lines: TechCardLine[] }) {
  const units = useTranslations("stock.units");
  return (
    <td colSpan={2} className="border-r border-black p-0 align-top">
      {name !== null ? (
        <div
          className={cn(
            "break-inside-avoid px-2 py-1 text-sm font-bold italic",
            lines.length > 0 && "border-b border-black",
          )}
        >
          {name}
        </div>
      ) : null}
      {lines.map((line, index) => (
        <div
          key={line.id}
          className={cn(
            "grid grid-cols-[32fr_14fr] break-inside-avoid",
            index < lines.length - 1 && "border-b border-black",
          )}
        >
          <div className="min-w-0 border-r border-black px-2 py-1 text-sm">{line.name}</div>
          <div className="px-2 py-1 text-right text-sm tabular-nums">
            {formatLineAmount(line.quantity, units(line.quantity_unit))}
          </div>
        </div>
      ))}
    </td>
  );
}

function ChapterBlock({ chapter }: { chapter: PrintChapter }) {
  return (
    <tr className="border-t border-black">
      <IngredientCell name={chapter.name} lines={chapter.lines} />
      <td className="px-2 py-1 align-top text-[13px] leading-5">
        {chapter.method.trim() ? <MarkdownView value={chapter.method} /> : null}
      </td>
    </tr>
  );
}

export function ExpandedPrintRows({ recipe }: { recipe: ExpandedRecipe }) {
  const units = useTranslations("stock.units");
  const rows: { key: string; name: string | null; lines: TechCardLine[] }[] = [];
  if (recipe.lines.length > 0) rows.push({ key: "base", name: null, lines: recipe.lines });
  for (const chapter of recipe.chapters) {
    const name =
      chapter.quantity === null || chapter.quantityUnit === null
        ? chapter.name
        : `${chapter.name} — ${formatLineAmount(chapter.quantity, units(chapter.quantityUnit))}`;
    rows.push({ key: chapter.key, name, lines: chapter.lines });
  }
  if (rows.length === 0) {
    return (
      <tr className="border-t border-black">
        <td colSpan={2} className="border-r border-black" />
        <td className="px-2 py-1 align-top text-[13px] leading-5">
          {recipe.method.trim() ? <MarkdownView value={recipe.method} /> : null}
        </td>
      </tr>
    );
  }
  return (
    <>
      {rows.map((row, index) => (
        <tr key={row.key} className="border-t border-black">
          <IngredientCell name={row.name} lines={row.lines} />
          {index === 0 ? (
            <td rowSpan={rows.length} className="px-2 py-1 align-top text-[13px] leading-5">
              {recipe.method.trim() ? <MarkdownView value={recipe.method} /> : null}
            </td>
          ) : null}
        </tr>
      ))}
    </>
  );
}

export function TechCardPrint({
  card,
  showPrintButton,
  expanded,
  techCards,
  semiProducts,
}: {
  card: TechCard;
  showPrintButton: boolean;
  expanded: boolean;
  techCards: TechCard[];
  semiProducts: SemiProduct[];
}) {
  const t = useTranslations("stock");
  const basis =
    card.kind === "weighted" && card.basis_weight_kg !== null
      ? t("basisKg", { weight: card.basis_weight_kg })
      : card.basis_quantity !== null
        ? t("basisPieces", { count: card.basis_quantity })
        : "";
  const chapters = printChapters(card, t("method"));
  const expandedRecipe = expanded ? expandRecipe(card.lines, card.sections, card.method, techCards, semiProducts) : null;
  const storage: string[] = [];
  if (card.shelf_life_seconds !== null) {
    storage.push(
      `${t("shelfLife")}: ${formatShelfLife(
        card.shelf_life_seconds,
        (count) => t("shelfLifeDays", { count }),
        (count) => t("shelfLifeHours", { count }),
      )}`,
    );
  }
  if (card.storage_temperature !== null) {
    storage.push(`${t("storageTemperature")}: ${card.storage_temperature}`);
  }

  return (
    <div>
      <article className="bg-white text-black [--ink:#111111]">
        <div className="flex items-start justify-between gap-4">
          <img src="/logo_print.png" alt="Sweet & Chill" className="h-16 w-auto" />
          {showPrintButton ? (
            <div className="print:hidden">
              <Button type="button" onClick={() => window.print()}>
                {t("print")}
              </Button>
            </div>
          ) : null}
        </div>
        <h1 className="mt-4 text-center text-xl font-bold uppercase tracking-wide">{card.name}</h1>
        {basis ? <p className="mt-1 text-center text-sm">{basis}</p> : null}
        {storage.length > 0 ? <p className="mt-1 text-center text-sm">{storage.join(" · ")}</p> : null}
        <table className="mt-5 w-full table-fixed border-collapse border border-black">
          <colgroup>
            <col className="w-[32%]" />
            <col className="w-[14%]" />
            <col className="w-[54%]" />
          </colgroup>
          <thead>
            <tr className="text-center text-xs font-bold uppercase tracking-wide">
              <th className="border-r border-black px-2 py-1.5 font-bold">{t("printIngredients")}</th>
              <th className="border-r border-black px-2 py-1.5 font-bold">{t("printWeight")}</th>
              <th className="px-2 py-1.5 font-bold">{t("printMethod")}</th>
            </tr>
          </thead>
          <tbody>
            {expandedRecipe !== null ? (
              <ExpandedPrintRows recipe={expandedRecipe} />
            ) : (
              chapters.map((chapter) => <ChapterBlock key={chapter.key} chapter={chapter} />)
            )}
          </tbody>
        </table>
      </article>
    </div>
  );
}
