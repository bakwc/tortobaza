"use client";

import { useTranslations } from "next-intl";
import { expandRecipe } from "@/components/menu/expandComposition";
import { MarkdownView } from "@/components/menu/MarkdownView";
import { NestedChapterBlocks } from "@/components/menu/TechCardPrint";
import { Button } from "@/components/ui/button";
import { formatQuantity } from "@/components/menu/ui";
import type { SemiProduct } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export function SemiProductPrint({
  product,
  expanded,
  semiProducts,
}: {
  product: SemiProduct;
  expanded: boolean;
  semiProducts: SemiProduct[];
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const yieldLine = `${t("yield")}: ${formatQuantity(product.yield_quantity)} ${units(product.unit)}`;
  const nestedChapters = expanded
    ? expandRecipe(
        product.lines.map((line) => ({
          ...line,
          nested_tech_card: null,
          nested_section: null,
        })),
        [],
        [],
        semiProducts,
      )
    : [];

  return (
    <div>
      <article className="bg-white text-black [--ink:#111111]">
        <div className="flex items-start justify-between gap-4">
          <img src="/logo_print.png" alt="Sweet & Chill" className="h-16 w-auto" />
          <div className="print:hidden">
            <Button type="button" onClick={() => window.print()}>
              {t("print")}
            </Button>
          </div>
        </div>
        <h1 className="mt-4 text-center text-xl font-bold uppercase tracking-wide">{product.name}</h1>
        <p className="mt-1 text-center text-sm">{yieldLine}</p>
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
            {nestedChapters.length > 0 ? <NestedChapterBlocks chapters={nestedChapters} /> : null}
            <tr className="border-t border-black">
                <td colSpan={2} className="border-r border-black p-0 align-top">
                  {nestedChapters.length > 0 ? (
                    <div
                      className={cn(
                        "break-inside-avoid px-2 py-1 text-sm font-bold italic",
                        product.lines.length > 0 && "border-b border-black",
                      )}
                    >
                      {product.name}
                    </div>
                  ) : null}
                  {product.lines.map((line, index) => (
                    <div
                      key={line.id}
                      className={cn(
                        "grid grid-cols-[32fr_14fr] break-inside-avoid",
                        index < product.lines.length - 1 && "border-b border-black",
                      )}
                    >
                      <div className="min-w-0 border-r border-black px-2 py-1 text-sm">{line.name}</div>
                      <div className="px-2 py-1 text-right text-sm tabular-nums">
                        {formatQuantity(line.quantity)} {units(line.quantity_unit)}
                      </div>
                    </div>
                  ))}
                </td>
                <td className="px-2 py-1 align-top text-[13px] leading-5">
                  {product.method.trim() ? <MarkdownView value={product.method} /> : null}
                </td>
              </tr>
          </tbody>
        </table>
      </article>
    </div>
  );
}
