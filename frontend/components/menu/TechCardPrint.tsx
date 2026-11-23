"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { expandRecipe, type ExpandedChapter, type TechCardLine } from "@/components/menu/expandComposition";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { formatShelfLife } from "@/components/menu/shelfLife";
import { pieceLineGrams } from "@/components/menu/techCardWeight";
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

function printChapters(card: TechCard, assemblyName: string | null): PrintChapter[] {
  if (card.sections.length === 0) {
    return [{ key: "base", name: assemblyName, lines: card.lines, method: card.method }];
  }
  const chapters: PrintChapter[] = [];
  for (const section of card.sections) {
    chapters.push({
      key: `section-${section.id}`,
      name: section.name,
      lines: section.lines,
      method: section.method,
    });
  }
  if (assemblyName !== null || card.method.trim() !== "") {
    chapters.push({ key: "base", name: assemblyName, lines: card.lines, method: card.method });
  } else if (card.lines.length > 0) {
    chapters.unshift({ key: "base", name: null, lines: card.lines, method: "" });
  }
  return chapters;
}

function lineAmount(
  line: TechCardLine,
  units: (unit: TechCardLine["quantity_unit"]) => string,
  cards: Map<number, TechCard>,
  gramsPerUnit: (ingredientId: number) => string | null,
): string {
  const amount = formatLineAmount(line.quantity, units(line.quantity_unit));
  const piece = pieceLineGrams(line.quantity, line.quantity_unit, line.nested_tech_card, cards, gramsPerUnit);
  if (piece === null) return amount;
  return `${amount} (${formatLineAmount(String(piece), units("g"))})`;
}

function IngredientCell({
  name,
  lines,
  cards,
  gramsPerUnit,
}: {
  name: string | null;
  lines: TechCardLine[];
  cards: Map<number, TechCard>;
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
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
            {lineAmount(line, units, cards, gramsPerUnit)}
          </div>
        </div>
      ))}
    </td>
  );
}

function ChapterBlock({
  chapter,
  cards,
  gramsPerUnit,
}: {
  chapter: PrintChapter;
  cards: Map<number, TechCard>;
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  return (
    <tr className="border-t border-black">
      <IngredientCell name={chapter.name} lines={chapter.lines} cards={cards} gramsPerUnit={gramsPerUnit} />
      <td className="px-2 py-1 align-top text-[13px] leading-5">
        {chapter.method.trim() ? <MarkdownView value={chapter.method} /> : null}
      </td>
    </tr>
  );
}

export function NestedChapterBlocks({
  chapters,
  cards,
  gramsPerUnit,
}: {
  chapters: ExpandedChapter[];
  cards: Map<number, TechCard>;
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  const units = useTranslations("stock.units");
  return (
    <>
      {chapters.map((chapter) => (
        <ChapterBlock
          key={chapter.key}
          cards={cards}
          gramsPerUnit={gramsPerUnit}
          chapter={{
            key: chapter.key,
            name:
              chapter.quantity === null || chapter.quantityUnit === null
                ? chapter.name
                : `${chapter.name} — ${formatLineAmount(chapter.quantity, units(chapter.quantityUnit))}`,
            lines: chapter.lines,
            method: chapter.method,
          }}
        />
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
  gramsPerUnit,
}: {
  card: TechCard;
  showPrintButton: boolean;
  expanded: boolean;
  techCards: TechCard[];
  semiProducts: SemiProduct[];
  gramsPerUnit: (ingredientId: number) => string | null;
}) {
  const t = useTranslations("stock");
  const basis =
    card.kind === "weighted" && card.basis_weight_kg !== null
      ? t("basisKg", { weight: card.basis_weight_kg })
      : card.basis_quantity !== null
        ? t("basisPieces", { count: card.basis_quantity })
        : "";
  const cardsById = useMemo(() => new Map(techCards.map((row) => [row.id, row])), [techCards]);
  const nestedChapters = expanded ? expandRecipe(card.lines, card.sections, techCards, semiProducts) : [];
  const assemblyName =
    nestedChapters.length > 0 || (card.sections.length > 0 && card.method.trim() !== "") ? card.name : null;
  const chapters = printChapters(card, assemblyName);
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
            {nestedChapters.length > 0 ? (
              <NestedChapterBlocks chapters={nestedChapters} cards={cardsById} gramsPerUnit={gramsPerUnit} />
            ) : null}
            {chapters.map((chapter) => (
              <ChapterBlock key={chapter.key} chapter={chapter} cards={cardsById} gramsPerUnit={gramsPerUnit} />
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}
