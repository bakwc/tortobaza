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
  quantity_unit: MenuUnit;
  loss_percent: string;
  unit_cost: string;
};

export type ComponentOption = { value: string; label: string; unit: MenuUnit; ingredient: boolean };

let draftCounter = 0;

export function newDraftKey(): string {
  draftCounter += 1;
  return `draft-${draftCounter}`;
}

export function componentValue(ref: {
  ingredient: number | null;
  semi_product: number | null;
  finished_good?: number | null;
}): string {
  if (ref.finished_good != null) {
    return `finished_good:${ref.finished_good}`;
  }
  return ref.ingredient !== null ? `ingredient:${ref.ingredient}` : `semi_product:${ref.semi_product}`;
}

export function componentRef(value: string): ComponentRefBody & { finished_good: number | null } {
  const separator = value.indexOf(":");
  const kind = value.slice(0, separator);
  const pk = Number(value.slice(separator + 1));
  if (kind === "ingredient") {
    return { ingredient: pk, semi_product: null, finished_good: null };
  }
  if (kind === "finished_good") {
    return { ingredient: null, semi_product: null, finished_good: pk };
  }
  return { ingredient: null, semi_product: pk, finished_good: null };
}

export function emptyLine(): ComponentLineDraft {
  return { key: newDraftKey(), component: "", quantity: "", quantity_unit: "g", loss_percent: "0", unit_cost: "" };
}

export function draftFromLine(
  line: ComponentRefBody & {
    quantity: string;
    loss_percent?: string;
    quantity_unit: MenuUnit;
    finished_good?: number | null;
  },
): ComponentLineDraft {
  return {
    key: newDraftKey(),
    component: componentValue(line),
    quantity: line.quantity,
    quantity_unit: line.quantity_unit,
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
    .map((row) => ({
      value: `ingredient:${row.id}`,
      label: `${ingredientLabel}: ${row.name}`,
      unit: row.unit,
      ingredient: true,
    }));
  if (semiFilter !== "none") {
    for (const row of semiProducts) {
      if (!row.is_active) continue;
      if (semiFilter === "produced" && !row.is_produced) continue;
      options.push({
        value: `semi_product:${row.id}`,
        label: `${semiLabel}: ${row.name}`,
        unit: row.unit,
        ingredient: false,
      });
    }
  }
  return options;
}

export function finishedGoodOptions(
  goods: { id: number; name: string }[],
  label: string,
): ComponentOption[] {
  return goods.map((row) => ({
    value: `finished_good:${row.id}`,
    label: `${label}: ${row.name}`,
    unit: "pcs",
    ingredient: false,
  }));
}

export function ComponentLinesEditor({
  lines,
  onChange,
  options,
  extraColumn,
  quantityLabel,
  chooseQuantityUnit,
}: {
  lines: ComponentLineDraft[];
  onChange: (lines: ComponentLineDraft[]) => void;
  options: ComponentOption[];
  extraColumn: "loss" | "unitCost" | null;
  quantityLabel: string;
  chooseQuantityUnit: boolean;
}) {
  const t = useTranslations("stock");
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
              onChange={(component) => {
                const next = options.find((row) => row.value === component);
                update(line.key, {
                  component,
                  quantity_unit: next === undefined ? line.quantity_unit : next.unit,
                });
              }}
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
                className="pr-16"
              />
              <QuantityUnitControl
                option={option}
                value={line.quantity_unit}
                chooseQuantityUnit={chooseQuantityUnit}
                onChange={(quantity_unit) => update(line.key, { quantity_unit })}
              />
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
    quantity_unit: line.quantity_unit,
    loss_percent: (line.loss_percent || "0").replace(",", "."),
  }));
}

export function QuantityUnitControl({
  option,
  value,
  chooseQuantityUnit,
  onChange,
}: {
  option: ComponentOption | undefined;
  value: MenuUnit;
  chooseQuantityUnit: boolean;
  onChange: (unit: MenuUnit) => void;
}) {
  const units = useTranslations("stock.units");
  if (option === undefined) {
    return <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]" />;
  }
  if (chooseQuantityUnit && option.ingredient && option.unit !== "g") {
    return (
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as MenuUnit)}
        className="absolute right-2 top-1/2 w-14 -translate-y-1/2 bg-transparent text-right text-xs text-[var(--muted-2)]"
      >
        <option value="g">{units("g")}</option>
        <option value={option.unit}>{units(option.unit)}</option>
      </select>
    );
  }
  return (
    <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
      {units(chooseQuantityUnit ? value : option.unit)}
    </span>
  );
}

export function linesToQuantityBody(lines: ComponentLineDraft[]) {
  return lines.map((line) => ({
    ...componentRef(line.component),
    quantity: line.quantity.replace(",", "."),
  }));
}
