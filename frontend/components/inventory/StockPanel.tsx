"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Card, CardTitle, Field, QueryState, formatMoney, formatQuantity, formatUnitCost } from "@/components/menu/ui";
import { useIngredientCategories, useIngredients, useStockLevels, useStockMovements } from "@/hooks/useStock";
import type { StockRow } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type StockGroup = { key: string; label: string; rows: StockRow[] };

function stockKey(row: StockRow): string {
  return `${row.ingredient ?? "i"}-${row.semi_product ?? "s"}-${row.finished_good ?? "f"}`;
}

function stockGroup(row: StockRow, categoryByIngredient: Map<number, number | null>): string {
  if (row.finished_good !== null) return "finished";
  if (row.semi_product !== null) return "semi";
  if (row.ingredient === null) return "none";
  const category = categoryByIngredient.get(row.ingredient);
  if (category === undefined || category === null) return "none";
  return String(category);
}

function stockGroups(
  rows: StockRow[],
  categoryByIngredient: Map<number, number | null>,
  categories: { id: number; name: string }[],
  labels: { none: string; semi: string; finished: string },
): StockGroup[] {
  const byGroup = new Map<string, StockRow[]>();
  for (const row of rows) {
    const key = stockGroup(row, categoryByIngredient);
    const groupRows = byGroup.get(key) ?? [];
    groupRows.push(row);
    byGroup.set(key, groupRows);
  }
  for (const groupRows of byGroup.values()) {
    groupRows.sort((left, right) => left.name.localeCompare(right.name));
  }
  return [
    ...categories.map((category) => ({ key: String(category.id), label: category.name })),
    { key: "none", label: labels.none },
    { key: "semi", label: labels.semi },
    { key: "finished", label: labels.finished },
  ]
    .map((group) => ({ ...group, rows: byGroup.get(group.key) ?? [] }))
    .filter((group) => group.rows.length > 0);
}

function MovementsDialog({ row, onClose }: { row: StockRow; onClose: () => void }) {
  const t = useTranslations("stock");
  const kinds = useTranslations("stock.movementKinds");
  const units = useTranslations("stock.units");
  const movements = useStockMovements({
    ingredient: row.ingredient,
    semi_product: row.semi_product,
    finished_good: row.finished_good,
  });
  return (
    <Dialog open onOpenChange={(value) => (value ? null : onClose())}>
      <DialogContent className="w-[min(800px,calc(100vw-1.5rem))] overflow-y-auto p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">{row.name}</DialogTitle>
        <DialogDescription className="text-sm text-[var(--muted-2)]">{t("movements")}</DialogDescription>
        <QueryState isLoading={movements.isLoading} isError={movements.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("date")}</th>
                <th className="py-2">{t("movementKind")}</th>
                <th className="py-2 text-right">{t("quantity")}</th>
                <th className="py-2 text-right">{t("unitCost")}</th>
              </tr>
            </thead>
            <tbody>
              {(movements.data ?? []).map((movement) => (
                <tr key={movement.id} className="border-t border-[var(--line)]">
                  <td className="py-2">{movement.date}</td>
                  <td className="py-2">
                    {kinds(movement.kind)}
                    {movement.document.type === "crm_order" ? ` #${movement.document.id}` : ""}
                  </td>
                  <td
                    className={cn(
                      "py-2 text-right",
                      Number(movement.quantity) < 0 ? "text-[var(--danger)]" : "text-emerald-700",
                    )}
                  >
                    {formatQuantity(movement.quantity)} {units(movement.unit)}
                  </td>
                  <td className="py-2 text-right">
                    {movement.unit_cost !== undefined ? formatMoney(movement.unit_cost) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </DialogContent>
    </Dialog>
  );
}

export function StockPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const [date, setDate] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selected, setSelected] = useState<StockRow | null>(null);
  const stock = useStockLevels(date === "" ? null : date);
  const ingredients = useIngredients();
  const categories = useIngredientCategories();
  const rows = (stock.data ?? []).filter((row) => row.is_active || Number(row.quantity) !== 0);
  const categoryByIngredient = new Map((ingredients.list.data ?? []).map((row) => [row.id, row.category]));
  const allGroups = stockGroups(rows, categoryByIngredient, categories.list.data ?? [], {
    none: t("noCategory"),
    semi: t("semiProduct"),
    finished: t("finishedGood"),
  });
  const query = search.trim().toLowerCase();
  const groups = allGroups
    .filter((group) => categoryFilter === "all" || group.key === categoryFilter)
    .map((group) => ({ ...group, rows: group.rows.filter((row) => row.name.toLowerCase().includes(query)) }))
    .filter((group) => group.rows.length > 0);
  const visibleRows = groups.flatMap((group) => group.rows);
  const hasCosts = visibleRows.some((row) => row.value !== undefined);
  const totalValue = visibleRows.reduce((sum, row) => sum + Number(row.value ?? "0"), 0);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <CardTitle>{t("inventory.stock")}</CardTitle>
          <Field label={t("onDate")}>
            <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </Field>
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
        <QueryState
          isLoading={stock.isLoading || ingredients.list.isLoading || categories.list.isLoading}
          isError={stock.isError || ingredients.list.isError || categories.list.isError}
        >
          {groups.length === 0 ? (
            <div className="mt-4 flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
              <p className="text-base font-semibold text-[var(--ink)]">{t("nothingFound")}</p>
            </div>
          ) : (
          <div className="mt-4 grid gap-4">
            {groups.map((group) => (
              <section key={group.key} className="overflow-hidden rounded-3xl border border-[var(--line)]">
                <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
                  <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">
                    {group.label}
                  </h3>
                  <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                    {group.rows.length}
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                    <tr>
                      <th className="px-4 py-2">{t("name")}</th>
                      <th className="px-4 py-2 text-right">{t("remaining")}</th>
                      {hasCosts ? <th className="px-4 py-2 text-right">{t("avgCost")}</th> : null}
                      {hasCosts ? <th className="px-4 py-2 text-right">{t("value")}</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {group.rows.map((row) => (
                      <tr
                        key={stockKey(row)}
                        onClick={() => setSelected(row)}
                        className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                      >
                        <td className="px-4 py-2">{row.name}</td>
                        <td className={cn("px-4 py-2 text-right", Number(row.quantity) < 0 ? "text-[var(--danger)]" : "")}>
                          {formatQuantity(row.quantity)} {units(row.unit)}
                        </td>
                        {hasCosts ? (
                          <td className="px-4 py-2 text-right">{formatUnitCost(row.avg_cost ?? "0")}</td>
                        ) : null}
                        {hasCosts ? <td className="px-4 py-2 text-right">{formatMoney(row.value ?? "0")}</td> : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ))}
            {hasCosts ? (
              <div className="flex items-center justify-between px-4 text-sm font-semibold">
                <span>{t("total")}</span>
                <span>{formatMoney(String(totalValue))}</span>
              </div>
            ) : null}
          </div>
          )}
        </QueryState>
      </Card>
      {selected ? <MovementsDialog row={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
