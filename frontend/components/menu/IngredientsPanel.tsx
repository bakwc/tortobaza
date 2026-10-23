"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Check, ChevronRight, Droplets, Hash, Package, Plus, Scale, Search, Trash2, Wheat } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import {
  Card,
  CardTitle,
  CheckboxField,
  ErrorText,
  Field,
  NativeSelect,
  QueryState,
  formatUnitCost,
} from "@/components/menu/ui";
import { useIngredientCategories, useIngredients, useSemiProducts, useTechCards } from "@/hooks/useStock";
import { Link } from "@/i18n/navigation";
import type { Ingredient, IngredientBody, MenuUnit, SemiProduct, TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

const UNIT_ICONS = { g: Scale, ml: Droplets, pcs: Hash };

function emptyIngredient(): IngredientBody {
  return {
    name: "",
    category: null,
    unit: "g",
    is_active: true,
    avg_cost: null,
    cost_quantity: null,
    grams_per_unit: null,
  };
}

function unitCostDraft(value: string): string {
  return value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}

function decimalNumber(value: string): number {
  return Number(value.replace(",", "."));
}

function trimDecimal(value: number): string {
  return unitCostDraft(String(Math.round(value * 1e6) / 1e6));
}

function packPrice(avgCost: string, costQuantity: string): string {
  return trimDecimal(decimalNumber(avgCost) * decimalNumber(costQuantity));
}

function priceForQuantity(avgCost: string, costQuantity: string, unitLabel: string): string {
  return `${formatUnitCost(packPrice(avgCost, costQuantity))} / ${unitCostDraft(costQuantity)} ${unitLabel}`;
}

function ingredientRequest(draft: IngredientBody): IngredientBody {
  const body: IngredientBody = {
    name: draft.name,
    category: draft.category,
    unit: draft.unit,
    is_active: draft.is_active,
    avg_cost: null,
    cost_quantity: null,
    grams_per_unit: draft.unit === "g" || draft.grams_per_unit === null ? null : draft.grams_per_unit.replace(",", "."),
  };
  if (draft.avg_cost !== null && draft.cost_quantity !== null) {
    const quantity = draft.cost_quantity.replace(",", ".");
    body.cost_quantity = quantity;
    body.avg_cost = trimDecimal(decimalNumber(draft.avg_cost) / decimalNumber(quantity));
  }
  if (body.avg_cost === null) {
    Reflect.deleteProperty(body, "avg_cost");
  }
  if (body.cost_quantity === null) {
    Reflect.deleteProperty(body, "cost_quantity");
  }
  return body;
}

function semiProductsWithIngredient(ingredientId: number, semiProducts: SemiProduct[]): Set<number> {
  const used = new Set<number>();
  for (const semi of semiProducts) {
    if (semi.lines.some((line) => line.ingredient === ingredientId)) used.add(semi.id);
  }
  let grew = true;
  while (grew) {
    grew = false;
    for (const semi of semiProducts) {
      if (used.has(semi.id)) continue;
      if (semi.lines.some((line) => line.semi_product !== null && used.has(line.semi_product))) {
        used.add(semi.id);
        grew = true;
      }
    }
  }
  return used;
}

function cardUsesIngredient(card: TechCard, ingredientId: number, semiIds: Set<number>): boolean {
  const lines = [...card.lines, ...card.sections.flatMap((section) => section.lines), ...card.modifier_lines];
  return lines.some(
    (line) => line.ingredient === ingredientId || (line.semi_product !== null && semiIds.has(line.semi_product)),
  );
}

function IngredientTechCards({ ingredientId }: { ingredientId: number }) {
  const t = useTranslations("stock");
  const techCards = useTechCards();
  const semiProducts = useSemiProducts();
  const semiIds = semiProductsWithIngredient(ingredientId, semiProducts.list.data ?? []);
  const cards = (techCards.list.data ?? []).filter((card) => cardUsesIngredient(card, ingredientId, semiIds));
  return (
    <div>
      <p className="text-sm font-semibold text-[var(--ink)]">{t("usedInTechCards")}</p>
      <QueryState
        isLoading={techCards.list.isLoading || semiProducts.list.isLoading}
        isError={techCards.list.isError || semiProducts.list.isError}
      >
        {cards.length === 0 ? (
          <p className="mt-2 text-sm text-[var(--muted-2)]">{t("notUsedInTechCards")}</p>
        ) : (
          <ul className="mt-2 divide-y divide-[var(--line)]">
            {cards.map((card) => (
              <li key={card.id}>
                <Link
                  href={`/menu?card=${card.id}`}
                  className="flex items-center justify-between gap-3 py-2 text-sm font-semibold text-[var(--ink)] hover:text-[var(--brand)]"
                >
                  <span className={cn(!card.is_active && "line-through")}>{card.name}</span>
                  {card.is_active ? null : (
                    <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-[11px] font-semibold text-[var(--muted-2)]">
                      {t("inactive")}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </QueryState>
    </div>
  );
}

function IngredientRow({ row, unitLabel, onOpen }: { row: Ingredient; unitLabel: string; onOpen: () => void }) {
  const t = useTranslations("stock");
  const UnitIcon = UNIT_ICONS[row.unit];
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        "group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--cream-soft)] focus-visible:bg-[var(--cream-soft)] focus-visible:outline-none",
        !row.is_active && "opacity-60",
      )}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--brand)]/10 text-[var(--brand)]">
        <UnitIcon className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={cn("font-semibold text-[var(--ink)]", !row.is_active && "line-through")}>{row.name}</p>
          {row.is_active ? null : (
            <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-[11px] font-semibold text-[var(--muted-2)]">
              {t("inactive")}
            </span>
          )}
        </div>
      </div>
      <span className="hidden shrink-0 items-center gap-1 rounded-full bg-[var(--cream)] px-2.5 py-1 text-xs font-semibold text-[var(--ink)] sm:flex">
        <UnitIcon className="h-3.5 w-3.5 text-[var(--brand)]" />
        {unitLabel}
      </span>
      {row.avg_cost !== undefined ? (
        <span className="shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
          {priceForQuantity(row.avg_cost, row.cost_quantity, unitLabel)}
        </span>
      ) : null}
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </button>
  );
}

export function IngredientsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const ingredients = useIngredients();
  const categories = useIngredientCategories();
  const [viewing, setViewing] = useState<Ingredient | null>(null);
  const [draft, setDraft] = useState<IngredientBody | null>(null);
  const [newCategory, setNewCategory] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  const openEdit = (row: Ingredient) => {
    ingredients.save.reset();
    ingredients.remove.reset();
    setViewing(row);
    setDraft({
      name: row.name,
      category: row.category,
      unit: row.unit,
      is_active: row.is_active,
      avg_cost: row.avg_cost === undefined ? null : packPrice(row.avg_cost, row.cost_quantity),
      cost_quantity: row.avg_cost === undefined ? null : unitCostDraft(row.cost_quantity),
      grams_per_unit: row.grams_per_unit === null ? null : unitCostDraft(row.grams_per_unit),
    });
  };
  const openNew = () => {
    ingredients.save.reset();
    ingredients.remove.reset();
    setViewing(null);
    setDraft(emptyIngredient());
  };
  const close = () => {
    setDraft(null);
    setViewing(null);
  };

  const rows = ingredients.list.data ?? [];
  const query = search.trim().toLowerCase();
  const allGroups = [
    ...(categories.list.data ?? []).map((category) => ({
      key: String(category.id),
      label: category.name,
      rows: rows.filter((row) => row.category === category.id),
    })),
    { key: "none", label: t("noCategory"), rows: rows.filter((row) => row.category === null) },
  ].filter((group) => group.rows.length > 0);
  const groups = allGroups
    .filter((group) => categoryFilter === "all" || group.key === categoryFilter)
    .map((group) => ({ ...group, rows: group.rows.filter((row) => row.name.toLowerCase().includes(query)) }))
    .filter((group) => group.rows.length > 0);
  const activeCount = rows.filter((row) => row.is_active).length;

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--ink)]">{t("menu.ingredients")}</h2>
          <Button type="button" onClick={openNew}>
            <Plus className="mr-1.5 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <div className="relative mt-5">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-2)]" />
          <Input
            value={search}
            placeholder={t("searchTechCards")}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-11"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            { key: "all", label: t("allCategories"), count: rows.length },
            ...allGroups.map((group) => ({ key: group.key, label: group.label, count: group.rows.length })),
          ].map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={() => setCategoryFilter(chip.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                categoryFilter === chip.key
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {chip.label}
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px]",
                  categoryFilter === chip.key ? "bg-white/25" : "bg-[var(--cream)]",
                )}
              >
                {chip.count}
              </span>
            </button>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3 border-t border-[var(--line)] pt-4 text-xs sm:gap-6 sm:text-sm">
          <div className="flex items-center gap-1.5 text-[var(--ink)]">
            <Package className="h-4 w-4 text-[var(--muted-2)]" />
            <span>{t("total")}</span>
            <span className="font-bold">{rows.length}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <Check className="h-4 w-4" />
            <span>{t("activeCount")}</span>
            <span className="font-bold">
              {activeCount} / {rows.length}
            </span>
          </div>
        </div>
      </Card>

      <QueryState isLoading={ingredients.list.isLoading} isError={ingredients.list.isError}>
        {groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
            <Wheat className="h-12 w-12 text-[var(--muted)]" />
            <p className="mt-4 text-base font-semibold text-[var(--ink)]">{t("nothingFound")}</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {groups.map((group) => (
              <section
                key={group.key}
                className="overflow-hidden rounded-3xl border border-[var(--line)] bg-white shadow-sm"
              >
                <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
                  <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">
                    {group.label}
                  </h3>
                  <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                    {group.rows.length}
                  </span>
                </div>
                <div className="divide-y divide-[var(--line)]">
                  {group.rows.map((row) => (
                    <IngredientRow key={row.id} row={row} unitLabel={units(row.unit)} onOpen={() => openEdit(row)} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryState>

      <Card>
        <CardTitle>{t("categories")}</CardTitle>
        <div className="mt-4 flex flex-wrap gap-2">
          {(categories.list.data ?? []).map((row) => (
            <span
              key={row.id}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] px-3 py-1 text-sm"
            >
              {row.name}
              <button
                type="button"
                aria-label={t("delete")}
                onClick={() => categories.remove.mutate(row.id)}
                className="text-[var(--muted-2)] hover:text-[var(--danger)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </span>
          ))}
        </div>
        <form
          className="mt-4 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            categories.save.mutate(
              {
                id: null,
                body: { name: newCategory, position: (categories.list.data ?? []).length },
              },
              { onSuccess: () => setNewCategory("") },
            );
          }}
        >
          <Input
            required
            value={newCategory}
            placeholder={t("newCategory")}
            onChange={(event) => setNewCategory(event.target.value)}
          />
          <Button type="submit" disabled={categories.save.isPending}>
            {t("add")}
          </Button>
        </form>
        <div className="mt-2">
          <ErrorText error={categories.save.error ?? categories.remove.error} />
        </div>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={close}
          title={viewing === null ? t("newIngredient") : draft.name}
          pending={ingredients.save.isPending}
          error={ingredients.save.error ?? ingredients.remove.error}
          submitLabel={t("save")}
          onSubmit={() =>
            ingredients.save.mutate(
              { id: viewing === null ? null : viewing.id, body: ingredientRequest(draft) },
              { onSuccess: close },
            )
          }
          onDelete={viewing === null ? null : () => ingredients.remove.mutate(viewing.id, { onSuccess: close })}
          deletePending={ingredients.remove.isPending}
          below={viewing === null ? null : <IngredientTechCards ingredientId={viewing.id} />}
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={t("name")} className="sm:col-span-3">
              <Input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            </Field>
            <Field label={t("category")}>
              <NativeSelect
                value={draft.category ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, category: event.target.value === "" ? null : Number(event.target.value) })
                }
              >
                <option value="">—</option>
                {(categories.list.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label={t("unit")}>
              <NativeSelect
                value={draft.unit}
                onChange={(event) => {
                  const unit = event.target.value as MenuUnit;
                  setDraft({ ...draft, unit, grams_per_unit: unit === "g" ? null : draft.grams_per_unit });
                }}
              >
                {UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {units(unit)}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            {draft.unit === "g" ? null : (
              <Field label={t(draft.unit === "ml" ? "density" : "pieceWeight")}>
                <Input
                  required
                  inputMode="decimal"
                  value={draft.grams_per_unit ?? ""}
                  onChange={(event) => setDraft({ ...draft, grams_per_unit: event.target.value })}
                />
              </Field>
            )}
            {draft.avg_cost !== null && draft.cost_quantity !== null ? (
              <Field label={t("avgCost")}>
                <Input
                  required
                  inputMode="decimal"
                  value={draft.avg_cost}
                  onChange={(event) => setDraft({ ...draft, avg_cost: event.target.value })}
                />
              </Field>
            ) : null}
            {draft.avg_cost !== null && draft.cost_quantity !== null ? (
              <Field label={`${t("costQuantity")}, ${units(draft.unit)}`}>
                <Input
                  required
                  inputMode="decimal"
                  value={draft.cost_quantity}
                  onChange={(event) => setDraft({ ...draft, cost_quantity: event.target.value })}
                />
              </Field>
            ) : null}
            <div className="flex items-end pb-3">
              <CheckboxField
                label={t("isActive")}
                checked={draft.is_active}
                onChange={(value) => setDraft({ ...draft, is_active: value })}
              />
            </div>
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
