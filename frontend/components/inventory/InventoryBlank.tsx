"use client";

import { Fragment, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { QueryState } from "@/components/menu/ui";
import { useIngredientCategories, useIngredients } from "@/hooks/useStock";
import type { Ingredient, MenuUnit } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";

const EXTRA_ROWS = 2;
const OTHER_ROWS = 8;

type BlankLine = { key: string; category: string; product: string };

type BlankGroup = { key: string; lines: BlankLine[] };

function blankGroups(
  ingredients: Ingredient[],
  categories: { id: number; name: string }[],
  noCategory: string,
  unitLabel: (unit: MenuUnit) => string,
): BlankGroup[] {
  const byCategory = new Map<string, Ingredient[]>();
  for (const row of ingredients) {
    if (!row.is_active) continue;
    const key = row.category === null ? "none" : String(row.category);
    const list = byCategory.get(key) ?? [];
    list.push(row);
    byCategory.set(key, list);
  }
  for (const list of byCategory.values()) {
    list.sort((left, right) => left.name.localeCompare(right.name));
  }
  return [
    ...categories.map((category) => ({ key: String(category.id), label: category.name })),
    { key: "none", label: noCategory },
  ]
    .filter((group) => (byCategory.get(group.key) ?? []).length > 0)
    .map((group) => {
      const lines: BlankLine[] = (byCategory.get(group.key) ?? []).map((row) => ({
        key: String(row.id),
        category: group.label,
        product: `${row.name}, ${unitLabel(row.unit)}`,
      }));
      for (let index = 0; index < EXTRA_ROWS; index += 1) {
        lines.push({ key: `${group.key}-extra-${index}`, category: group.label, product: "" });
      }
      return { key: group.key, lines };
    });
}

function printedDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  if (year === undefined || month === undefined || day === undefined) return iso;
  return `${day}.${month}.${year}`;
}

function LineRow({ line }: { line: BlankLine }) {
  return (
    <tr className="break-inside-avoid">
      <td className="border border-black px-1.5 py-1">{line.category}</td>
      <td className="border border-black px-1.5 py-1">{line.product}</td>
      <td className="border border-black px-1.5 py-1" />
      <td className="border border-black px-1.5 py-1" />
      <td className="border border-black px-1.5 py-1" />
    </tr>
  );
}

export function InventoryBlank() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const ingredients = useIngredients();
  const categories = useIngredientCategories();
  const [date, setDate] = useState(getTbilisiTodayIsoDate);
  const groups = blankGroups(ingredients.list.data ?? [], categories.list.data ?? [], t("noCategory"), (unit) =>
    units(unit),
  );
  const otherLines: BlankLine[] = Array.from({ length: OTHER_ROWS }, (_, index) => ({
    key: `other-${index}`,
    category: t("blankOther"),
    product: "",
  }));

  return (
    <QueryState
      isLoading={ingredients.list.isLoading || categories.list.isLoading}
      isError={ingredients.list.isError || categories.list.isError}
    >
      <div>
        <div className="mb-4 flex justify-end print:hidden">
          <Button type="button" onClick={() => window.print()}>
            {t("print")}
          </Button>
        </div>
        <article className="bg-white text-sm text-black">
          <h1 className="bg-[#FFF2CC] py-3 text-center text-xl font-bold uppercase tracking-wide [print-color-adjust:exact]">
            {t("blankTitle")}
          </h1>
          <div className="flex items-center justify-end gap-2 py-2">
            <span className="font-semibold">{t("blankDate")}:</span>
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              className="border-b border-black bg-transparent px-1 print:hidden"
            />
            <span className="hidden print:inline">{printedDate(date)}</span>
          </div>
          <table className="w-full table-fixed border-collapse text-[11px] leading-tight">
            <colgroup>
              <col className="w-[17%]" />
              <col className="w-[26%]" />
              <col className="w-[13%]" />
              <col className="w-[17%]" />
              <col className="w-[27%]" />
            </colgroup>
            <thead className="table-header-group">
              <tr className="break-inside-avoid text-center text-[10px] font-bold uppercase">
                <th className="border border-black px-1.5 py-1.5">{t("blankCategory")}</th>
                <th className="border border-black px-1.5 py-1.5">{t("blankProduct")}</th>
                <th className="border border-black px-1.5 py-1.5">{t("blankRemaining")}</th>
                <th className="border border-black px-1.5 py-1.5">{t("blankToBuy")}</th>
                <th className="border border-black px-1.5 py-1.5">{t("blankComment")}</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group, groupIndex) => (
                <Fragment key={group.key}>
                  {groupIndex > 0 ? (
                    <tr className="break-inside-avoid">
                      <td colSpan={5} className="h-3 border-0 p-0" />
                    </tr>
                  ) : null}
                  {group.lines.map((line) => (
                    <LineRow key={line.key} line={line} />
                  ))}
                </Fragment>
              ))}
              <tr className="break-inside-avoid">
                <td colSpan={5} className="h-3 border-0 p-0" />
              </tr>
              {otherLines.map((line) => (
                <LineRow key={line.key} line={line} />
              ))}
            </tbody>
          </table>
        </article>
      </div>
    </QueryState>
  );
}
