"use client";

import { useTranslations } from "next-intl";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { Button } from "@/components/ui/button";
import { formatQuantity } from "@/components/menu/ui";
import type { RecipeLine, TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type PrintChapter = {
  key: string;
  name: string | null;
  lines: RecipeLine[];
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

function ChapterBlock({ chapter }: { chapter: PrintChapter }) {
  const units = useTranslations("stock.units");
  return (
    <div className="grid grid-cols-[48fr_14fr_38fr] break-inside-avoid">
      <div className="col-span-2 border-r border-black">
        {chapter.name !== null ? (
          <div
            className={cn(
              "px-2 py-1 text-sm font-bold italic",
              chapter.lines.length > 0 && "border-b border-black",
            )}
          >
            {chapter.name}
          </div>
        ) : null}
        {chapter.lines.map((line, index) => (
          <div
            key={line.id}
            className={cn(
              "grid grid-cols-[48fr_14fr]",
              index < chapter.lines.length - 1 && "border-b border-black",
            )}
          >
            <div className="min-w-0 border-r border-black px-2 py-1 text-sm">{line.name}</div>
            <div className="px-2 py-1 text-right text-sm tabular-nums">
              {formatQuantity(line.quantity)} {units(line.unit)}
            </div>
          </div>
        ))}
      </div>
      <div className="min-w-0 px-2 py-1 text-[13px] leading-5">
        {chapter.method.trim() ? <MarkdownView value={chapter.method} /> : null}
      </div>
    </div>
  );
}

export function TechCardPrint({ card }: { card: TechCard }) {
  const t = useTranslations("stock");
  const basis =
    card.kind === "weighted" && card.basis_weight_kg !== null
      ? t("basisKg", { weight: card.basis_weight_kg })
      : card.basis_quantity !== null
        ? t("basisPieces", { count: card.basis_quantity })
        : "";
  const chapters = printChapters(card, t("method"));

  return (
    <div>
      <div className="mb-6 flex justify-end print:hidden">
        <Button type="button" onClick={() => window.print()}>
          {t("print")}
        </Button>
      </div>
      <article className="bg-white text-black [--ink:#111111]">
        <div className="flex justify-end">
          <img src="/sweet_chill_logo.png" alt="Sweet & Chill" className="h-16 w-auto" />
        </div>
        <h1 className="mt-4 text-center text-xl font-bold uppercase tracking-wide">{card.name}</h1>
        {basis ? <p className="mt-1 text-center text-sm">{basis}</p> : null}
        <div className="mt-5 border border-black">
          <div className="grid grid-cols-[48fr_14fr_38fr] border-b border-black text-center text-xs font-bold uppercase tracking-wide">
            <div className="border-r border-black px-2 py-1.5">{t("printIngredients")}</div>
            <div className="border-r border-black px-2 py-1.5">{t("printWeight")}</div>
            <div className="px-2 py-1.5">{t("printMethod")}</div>
          </div>
          <div className="divide-y divide-black">
            {chapters.map((chapter) => (
              <ChapterBlock key={chapter.key} chapter={chapter} />
            ))}
          </div>
        </div>
      </article>
    </div>
  );
}
