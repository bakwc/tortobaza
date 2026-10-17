"use client";

import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchSelect } from "@/components/menu/SearchSelect";
import type { ComponentRefBody, Ingredient, MenuUnit, SemiProduct } from "@/lib/api/types";

export type ComponentLineDraft = {
  key: string;
  component: string;
  quantity: string;
  loss_percent: string;
  unit_cost: string;
};

export type ComponentOption = { value: string; label: string; unit: MenuUnit };

let draftCounter = 0;

export function newDraftKey(): string {
  draftCounter += 1;
  return `draft-${draftCounter}`;
}

export function componentValue(ref: ComponentRefBody): string {
  return ref.ingredient !== null ? `ingredient:${ref.ingredient}` : `semi_product:${ref.semi_product}`;
}

export function componentRef(value: string): ComponentRefBody {
  const [kind, id] = value.split(":");
  return kind === "ingredient"
    ? { ingredient: Number(id), semi_product: null }
    : { ingredient: null, semi_product: Number(id) };
}

export function emptyLine(): ComponentLineDraft {
  return { key: newDraftKey(), component: "", quantity: "", loss_percent: "0", unit_cost: "" };
}

export function draftFromLine(line: ComponentRefBody & { quantity: string; loss_percent?: string }): ComponentLineDraft {
  return {
    key: newDraftKey(),
    component: componentValue(line),
    quantity: line.quantity,
    loss_percent: line.loss_percent ?? "0",
    unit_cost: "",
  };
}

export function componentOptions(
  ingredients: Ingredient[],
  semiProducts: SemiProduct[],
  semiFilter: "all" | "produced" | "none",
  ingredientLabel: string,
  semiLabel: string,
): ComponentOption[] {
  const options: ComponentOption[] = ingredients
    .filter((row) => row.is_active)
    .map((row) => ({ value: `ingredient:${row.id}`, label: `${ingredientLabel}: ${row.name}`, unit: row.unit }));
  if (semiFilter !== "none") {
    for (const row of semiProducts) {
      if (!row.is_active) continue;
      if (semiFilter === "produced" && !row.is_produced) continue;
      options.push({ value: `semi_product:${row.id}`, label: `${semiLabel}: ${row.name}`, unit: row.unit });
    }
  }
  return options;
}

export function ComponentLinesEditor({
  lines,
  onChange,
  options,
  extraColumn,
  quantityLabel,
}: {
  lines: ComponentLineDraft[];
  onChange: (lines: ComponentLineDraft[]) => void;
  options: ComponentOption[];
  extraColumn: "loss" | "unitCost" | null;
  quantityLabel: string;
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const update = (key: string, patch: Partial<ComponentLineDraft>) =>
    onChange(lines.map((line) => (line.key === key ? { ...line, ...patch } : line)));

  return (
    <div className="grid gap-2">
      {lines.map((line) => {
        const option = options.find((row) => row.value === line.component);
        return (
          <div key={line.key} className="grid grid-cols-[1fr_auto] gap-2 sm:grid-cols-[1fr_9rem_7rem_auto]">
            <SearchSelect
              options={options}
              value={line.component}
              onChange={(component) => update(line.key, { component })}
              placeholder={t("chooseComponent")}
              required={true}
              className="col-span-2 sm:col-span-1"
            />
            <div className="relative">
              <Input
                required
                inputMode="decimal"
                placeholder={quantityLabel}
                value={line.quantity}
                onChange={(event) => update(line.key, { quantity: event.target.value })}
                className="pr-12"
              />
              <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                {option ? units(option.unit) : ""}
              </span>
            </div>
            {extraColumn === "loss" ? (
              <div className="relative">
                <Input
                  inputMode="decimal"
                  placeholder={t("lossPercent")}
                  value={line.loss_percent}
                  onChange={(event) => update(line.key, { loss_percent: event.target.value })}
                  className="pr-8"
                />
                <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                  %
                </span>
              </div>
            ) : extraColumn === "unitCost" ? (
              <Input
                inputMode="decimal"
                placeholder={t("unitCost")}
                value={line.unit_cost}
                onChange={(event) => update(line.key, { unit_cost: event.target.value })}
              />
            ) : (
              <span className="hidden sm:block" />
            )}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={t("removeLine")}
              onClick={() => onChange(lines.filter((row) => row.key !== line.key))}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        );
      })}
      <div>
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...lines, emptyLine()])}>
          <Plus className="mr-1 h-4 w-4" />
          {t("addLine")}
        </Button>
      </div>
    </div>
  );
}

export function linesToBody(lines: ComponentLineDraft[]) {
  return lines.map((line) => ({
    ...componentRef(line.component),
    quantity: line.quantity.replace(",", "."),
    loss_percent: (line.loss_percent || "0").replace(",", "."),
  }));
}

export function linesToQuantityBody(lines: ComponentLineDraft[]) {
  return lines.map((line) => ({
    ...componentRef(line.component),
    quantity: line.quantity.replace(",", "."),
  }));
}
