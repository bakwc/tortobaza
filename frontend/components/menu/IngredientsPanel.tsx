"use client";

import { Fragment, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, ChevronRight, Droplets, Hash, Package, Pencil, Plus, Scale, Search, Trash2, Wheat } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
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
import { useIngredientCategories, useIngredients } from "@/hooks/useStock";
import type { Ingredient, IngredientBody, MenuUnit } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

const UNIT_ICONS = { g: Scale, ml: Droplets, pcs: Hash };

function emptyIngredient(): IngredientBody {
  return { name: "", category: null, unit: "g", is_active: true, avg_cost: null };
}

function unitCostDraft(value: string): string {
  return value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
}

function ingredientRequest(draft: IngredientBody): IngredientBody {
  const body: IngredientBody = {
    name: draft.name,
    category: draft.category,
    unit: draft.unit,
    is_active: draft.is_active,
    avg_cost: draft.avg_cost === null ? null : draft.avg_cost.replace(",", "."),
  };
  if (body.avg_cost === null) {
    Reflect.deleteProperty(body, "avg_cost");
  }
  return body;
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
        <span className="w-24 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
          {formatUnitCost(row.avg_cost)}
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
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [viewing, setViewing] = useState<Ingredient | null>(null);
  const [draft, setDraft] = useState<IngredientBody | null>(null);
  const [newCategory, setNewCategory] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const current =
    viewing === null ? null : (ingredients.list.data ?? []).find((row) => row.id === viewing.id) ?? viewing;

  const openView = (row: Ingredient) => {
    ingredients.save.reset();
    ingredients.remove.reset();
    setViewing(row);
    setDraft(null);
    setMode("view");
  };
  const openNew = () => {
    ingredients.save.reset();
    ingredients.remove.reset();
    setViewing(null);
    setDraft(emptyIngredient());
    setMode("edit");
  };
  const openEdit = () => {
    if (current === null) return;
    setDraft({
      name: current.name,
      category: current.category,
      unit: current.unit,
      is_active: current.is_active,
      avg_cost: current.avg_cost === undefined ? null : unitCostDraft(current.avg_cost),
    });
    setMode("edit");
  };
  const close = () => {
    setMode(null);
    setDraft(null);
    setViewing(null);
  };
  const cancelEdit = () => {
    setDraft(null);
    if (viewing === null) close();
    else setMode("view");
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
  const badges =
    current === null
      ? []
      : [current.category_name ?? "", current.is_active ? "" : t("inactive")].filter((badge) => badge !== "");
  const stats =
    current === null
      ? []
      : [
          { label: t("unit"), value: units(current.unit) },
          ...(current.avg_cost !== undefined ? [{ label: t("avgCost"), value: formatUnitCost(current.avg_cost) }] : []),
        ];

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
                    <IngredientRow key={row.id} row={row} unitLabel={units(row.unit)} onOpen={() => openView(row)} />
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

      {mode === "view" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <div className="flex flex-wrap items-start justify-between gap-3 pr-10">
              <div className="grid min-w-0 gap-1.5">
                <DialogTitle className="text-2xl font-semibold leading-tight text-[var(--ink)]">{current.name}</DialogTitle>
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
              <Button type="button" size="sm" variant="outline" onClick={openEdit}>
                <Pencil className="mr-1 h-4 w-4" />
                {t("edit")}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      ) : null}

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : cancelEdit())}
          onCancel={cancelEdit}
          title={viewing === null ? t("newIngredient") : draft.name}
          pending={ingredients.save.isPending}
          error={ingredients.save.error ?? ingredients.remove.error}
          submitLabel={t("save")}
          onSubmit={() =>
            ingredients.save.mutate(
              { id: viewing === null ? null : viewing.id, body: ingredientRequest(draft) },
              {
                onSuccess: (saved) => {
                  setViewing(saved);
                  setDraft(null);
                  setMode("view");
                },
              },
            )
          }
          onDelete={viewing === null ? null : () => ingredients.remove.mutate(viewing.id, { onSuccess: close })}
          deletePending={ingredients.remove.isPending}
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
                onChange={(event) => setDraft({ ...draft, unit: event.target.value as MenuUnit })}
              >
                {UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {units(unit)}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            {draft.avg_cost !== null ? (
              <Field label={t("avgCost")}>
                <Input
                  required
                  inputMode="decimal"
                  value={draft.avg_cost}
                  onChange={(event) => setDraft({ ...draft, avg_cost: event.target.value })}
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
