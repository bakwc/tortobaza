"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { componentRef, componentValue } from "@/components/menu/ComponentLinesEditor";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, QueryState, formatQuantity } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import {
  useCloseInventoryCount,
  useIngredientCategories,
  useIngredients,
  useInventoryCounts,
  useRecountInventoryCount,
  useStockLevels,
} from "@/hooks/useStock";
import { Link } from "@/i18n/navigation";
import type { InventoryCount, MenuUnit, StockRow } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type CountDraft = { date: string; comment: string; quantities: Record<string, string> };

type CountItem = {
  key: string;
  name: string;
  unit: MenuUnit;
  group: string;
  expected: string;
};

type CountGroup = { key: string; label: string; rows: CountItem[] };

function draftFrom(row: InventoryCount | null): CountDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), comment: "", quantities: {} };
  }
  const quantities: Record<string, string> = {};
  for (const line of row.lines) {
    quantities[componentValue(line)] = line.actual_quantity;
  }
  return { date: row.date, comment: row.comment, quantities };
}

function filled(quantities: Record<string, string>, key: string): boolean {
  return (quantities[key] ?? "").trim() !== "";
}

function parsedQuantity(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const number = Number(trimmed.replace(",", "."));
  return Number.isFinite(number) ? number : null;
}

function differenceClass(difference: number): string {
  if (difference < 0) return "text-[var(--danger)]";
  if (difference > 0) return "text-emerald-700";
  return "";
}

function itemGroup(
  row: { ingredient: number | null; semi_product: number | null; finished_good: number | null },
  categoryByIngredient: Map<number, number | null>,
): string {
  if (row.finished_good !== null) return "finished";
  if (row.semi_product !== null) return "semi";
  if (row.ingredient === null) return "none";
  const category = categoryByIngredient.get(row.ingredient);
  if (category === undefined || category === null) return "none";
  return String(category);
}

function countGroups(
  items: CountItem[],
  categories: { id: number; name: string }[],
  labels: { none: string; semi: string; finished: string },
): CountGroup[] {
  const byGroup = new Map<string, CountItem[]>();
  for (const item of items) {
    const rows = byGroup.get(item.group) ?? [];
    rows.push(item);
    byGroup.set(item.group, rows);
  }
  for (const rows of byGroup.values()) {
    rows.sort((left, right) => left.name.localeCompare(right.name));
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

function listedRow(row: StockRow, quantities: Record<string, string>): boolean {
  return row.is_active || Number(row.quantity) !== 0 || filled(quantities, componentValue(row));
}

function ClosedCountView({
  count,
  categories,
  categoryByIngredient,
}: {
  count: InventoryCount;
  categories: { id: number; name: string }[];
  categoryByIngredient: Map<number, number | null>;
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const items: CountItem[] = count.lines.map((line) => ({
    key: String(line.id),
    name: line.name,
    unit: line.unit,
    group: itemGroup(line, categoryByIngredient),
    expected: line.expected_quantity ?? "0",
  }));
  const actualByKey = new Map(count.lines.map((line) => [String(line.id), line.actual_quantity]));
  const groups = countGroups(items, categories, {
    none: t("noCategory"),
    semi: t("semiProduct"),
    finished: t("finishedGood"),
  });
  return (
    <div className="grid gap-4">
      {groups.map((group) => (
        <section key={group.key} className="overflow-hidden rounded-3xl border border-[var(--line)]">
          <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
            <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">{group.label}</h3>
            <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
              {group.rows.length}
            </span>
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="px-4 py-2">{t("name")}</th>
                <th className="px-4 py-2 text-right">{t("expected")}</th>
                <th className="px-4 py-2 text-right">{t("actual")}</th>
                <th className="px-4 py-2 text-right">{t("difference")}</th>
              </tr>
            </thead>
            <tbody>
              {group.rows.map((row) => {
                const actual = actualByKey.get(row.key) ?? "0";
                const difference = Number(actual) - Number(row.expected);
                return (
                  <tr key={row.key} className="border-t border-[var(--line)]">
                    <td className="px-4 py-2">{row.name}</td>
                    <td className="px-4 py-2 text-right">
                      {formatQuantity(row.expected)} {units(row.unit)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      {formatQuantity(actual)} {units(row.unit)}
                    </td>
                    <td className={cn("px-4 py-2 text-right", differenceClass(difference))}>
                      {formatQuantity(String(difference))} {units(row.unit)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function CountLines({
  items,
  categories,
  quantities,
  onQuantities,
}: {
  items: CountItem[];
  categories: { id: number; name: string }[];
  quantities: Record<string, string>;
  onQuantities: (quantities: Record<string, string>) => void;
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const allGroups = countGroups(items, categories, {
    none: t("noCategory"),
    semi: t("semiProduct"),
    finished: t("finishedGood"),
  });
  const query = search.trim().toLowerCase();
  const groups = allGroups
    .filter((group) => categoryFilter === "all" || group.key === categoryFilter)
    .map((group) => ({
      key: group.key,
      label: group.label,
      total: group.rows.length,
      counted: group.rows.filter((row) => filled(quantities, row.key)).length,
      rows: group.rows.filter((row) => row.name.toLowerCase().includes(query)),
    }))
    .filter((group) => group.rows.length > 0);
  const setQuantity = (key: string, quantity: string) => onQuantities({ ...quantities, [key]: quantity });

  return (
    <div className="grid gap-4">
      <p className="text-xs text-[var(--muted-2)]">{t("countLegend")}</p>
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-2)]" />
        <Input
          value={search}
          placeholder={t("searchTechCards")}
          onChange={(event) => setSearch(event.target.value)}
          className="pl-11"
        />
      </div>
      <div className="flex flex-wrap gap-2">
        {[
          { key: "all", label: t("allCategories"), count: items.length },
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
      {groups.length === 0 ? (
        <p className="py-6 text-center text-sm text-[var(--muted-2)]">{t("nothingFound")}</p>
      ) : (
        groups.map((group) => (
          <section key={group.key} className="overflow-hidden rounded-3xl border border-[var(--line)]">
            <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
              <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">
                {group.label}
              </h3>
              <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                {group.counted}/{group.total}
              </span>
            </div>
            <div className="divide-y divide-[var(--line)]">
                {group.rows.map((row) => {
                  const value = quantities[row.key] ?? "";
                  return (
                    <div key={row.key} className="flex flex-wrap items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-[var(--ink)]">{row.name}</p>
                        <p className="text-xs text-[var(--muted-2)]">
                          {t("expected")}: {formatQuantity(row.expected)} {units(row.unit)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          inputMode="decimal"
                          placeholder={t("notCounted")}
                          value={value}
                          onChange={(event) => setQuantity(row.key, event.target.value)}
                          className="w-32"
                        />
                        {value.trim() === "" ? null : (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            aria-label={t("clearCount")}
                            onClick={() => setQuantity(row.key, "")}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>
        ))
      )}
    </div>
  );
}

export function InventoryCountsPanel() {
  const t = useTranslations("stock");
  const counts = useInventoryCounts();
  const closeCount = useCloseInventoryCount();
  const recountCount = useRecountInventoryCount();
  const ingredients = useIngredients();
  const categoryQuery = useIngredientCategories();
  const [editing, setEditing] = useState<InventoryCount | null>(null);
  const [draft, setDraft] = useState<CountDraft | null>(null);
  const stock = useStockLevels(draft?.date ?? null);
  const canEdit = useCan("edit_inventory");
  const categoryRows = categoryQuery.list.data ?? [];
  const categoryByIngredient = new Map((ingredients.list.data ?? []).map((row) => [row.id, row.category]));
  const items: CountItem[] = (stock.data ?? [])
    .filter((row) => draft !== null && listedRow(row, draft.quantities))
    .map((row) => ({
      key: componentValue(row),
      name: row.name,
      unit: row.unit,
      group: itemGroup(row, categoryByIngredient),
      expected: row.quantity,
    }));

  const open = (row: InventoryCount | null) => {
    counts.save.reset();
    counts.remove.reset();
    closeCount.reset();
    recountCount.reset();
    setEditing(row);
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  const body = (value: CountDraft) => ({
    date: value.date,
    comment: value.comment,
    lines: Object.entries(value.quantities)
      .filter(([, quantity]) => quantity.trim() !== "")
      .map(([component, quantity]) => ({
        ...componentRef(component),
        actual_quantity: quantity.replace(",", ".").trim(),
      })),
  });

  const isClosed = editing?.status === "closed";

  const closeAfterSave = useRef(false);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.inventoryCounts")}</CardTitle>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href="/inventory/blank">{t("inventory.printBlank")}</Link>
            </Button>
            {canEdit ? (
              <Button type="button" size="sm" onClick={() => open(null)}>
                <Plus className="mr-1 h-4 w-4" />
                {t("add")}
              </Button>
            ) : null}
          </div>
        </div>
        <p className="mt-2 text-xs text-[var(--muted-2)]">{t("inventoryCountHint")}</p>
        <QueryState isLoading={counts.list.isLoading} isError={counts.list.isError}>
          <div className="mt-4 grid gap-2">
            {(counts.list.data ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <span className="font-medium text-[var(--ink)]">
                  {row.date} · {t("positionsCount", { count: row.lines.length })}
                </span>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-xs font-semibold",
                    row.status === "closed" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800",
                  )}
                >
                  {row.status === "closed" ? t("statusClosed") : t("statusDraft")}
                </span>
              </button>
            ))}
          </div>
        </QueryState>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editing === null ? t("newInventoryCount") : `${t("inventory.inventoryCounts")} · ${editing.date}`}
          pending={counts.save.isPending}
          error={counts.save.error ?? counts.remove.error ?? closeCount.error ?? recountCount.error}
          submitLabel={canEdit && !isClosed ? t("saveDraft") : null}
          onSubmit={() => {
            const closeAfter = closeAfterSave.current;
            closeAfterSave.current = false;
            counts.save.mutate(
              { id: editing ? editing.id : null, body: body(draft) },
              {
                onSuccess: (saved) => {
                  setEditing(saved);
                  if (closeAfter) {
                    closeCount.mutate(saved.id, { onSuccess: (closed) => setEditing(closed) });
                  }
                },
              },
            );
          }}
          onDelete={canEdit && editing !== null ? () => counts.remove.mutate(editing.id, { onSuccess: close }) : null}
          deletePending={counts.remove.isPending}
          headerAction={null}
          below={null}
        >
          {isClosed && editing ? (
            <>
              {canEdit ? (
                <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--cream)] p-4">
                  <p className="flex-1 text-sm text-[var(--ink)]">{t("recountCountHint")}</p>
                  <Button
                    type="button"
                    disabled={recountCount.isPending}
                    onClick={() => recountCount.mutate(editing.id, { onSuccess: (saved) => setEditing(saved) })}
                  >
                    {recountCount.isPending ? <Spinner className="h-4 w-4" /> : t("recountCount")}
                  </Button>
                </div>
              ) : null}
              <ClosedCountView count={editing} categories={categoryRows} categoryByIngredient={categoryByIngredient} />
            </>
          ) : (
            <>
              {canEdit ? (
                <div className="flex flex-wrap justify-end gap-2">
                  {editing !== null ? (
                    <Button
                      type="button"
                      variant="outline"
                      disabled={counts.remove.isPending}
                      onClick={() => counts.remove.mutate(editing.id, { onSuccess: close })}
                    >
                      {counts.remove.isPending ? <Spinner className="h-4 w-4" /> : t("delete")}
                    </Button>
                  ) : null}
                  <Button
                    type="submit"
                    disabled={counts.save.isPending}
                    onClick={() => {
                      closeAfterSave.current = false;
                    }}
                  >
                    {counts.save.isPending ? <Spinner className="h-4 w-4" /> : t("saveDraft")}
                  </Button>
                  {editing !== null ? (
                    <Button
                      type="submit"
                      disabled={closeCount.isPending || counts.save.isPending}
                      onClick={() => {
                        closeAfterSave.current = true;
                      }}
                    >
                      {closeCount.isPending ? <Spinner className="h-4 w-4" /> : t("closeCount")}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t("date")}>
                  <Input
                    type="date"
                    required
                    value={draft.date}
                    onChange={(event) => setDraft({ ...draft, date: event.target.value })}
                  />
                </Field>
                <Field label={t("comment")} className="sm:col-span-2">
                  <Textarea
                    value={draft.comment}
                    onChange={(event) => setDraft({ ...draft, comment: event.target.value })}
                  />
                </Field>
              </div>
              <QueryState
                isLoading={stock.isLoading || ingredients.list.isLoading || categoryQuery.list.isLoading}
                isError={stock.isError || ingredients.list.isError || categoryQuery.list.isError}
              >
                <CountLines
                  items={items}
                  categories={categoryRows}
                  quantities={draft.quantities}
                  onQuantities={(quantities) => setDraft({ ...draft, quantities })}
                />
              </QueryState>
              {canEdit && editing ? (
                <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--cream)] p-4">
                  <p className="flex-1 text-sm text-[var(--ink)]">{t("closeCountHint")}</p>
                  <Button
                    type="submit"
                    disabled={closeCount.isPending || counts.save.isPending}
                    onClick={() => {
                      closeAfterSave.current = true;
                    }}
                  >
                    {closeCount.isPending ? <Spinner className="h-4 w-4" /> : t("closeCount")}
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </EditorDialog>
      ) : null}
    </div>
  );
}
