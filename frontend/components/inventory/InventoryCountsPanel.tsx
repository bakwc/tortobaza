"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import {
  ComponentLinesEditor,
  componentOptions,
  componentRef,
  componentValue,
  newDraftKey,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, QueryState, formatQuantity } from "@/components/menu/ui";
import { useCurrentUser } from "@/hooks/useAuth";
import {
  useCloseInventoryCount,
  useIngredients,
  useInventoryCounts,
  useSemiProducts,
  useStockLevels,
} from "@/hooks/useStock";
import type { InventoryCount } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type CountDraft = { date: string; comment: string; lines: ComponentLineDraft[] };

function draftFrom(row: InventoryCount | null): CountDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), comment: "", lines: [] };
  }
  return {
    date: row.date,
    comment: row.comment,
    lines: row.lines.map((line) => ({
      key: newDraftKey(),
      component: componentValue(line),
      quantity: line.actual_quantity,
      loss_percent: "0",
      unit_cost: line.unit_cost ?? "",
    })),
  };
}

function ClosedCountView({ count }: { count: InventoryCount }) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
        <tr>
          <th className="py-2">{t("name")}</th>
          <th className="py-2 text-right">{t("expected")}</th>
          <th className="py-2 text-right">{t("actual")}</th>
          <th className="py-2 text-right">{t("difference")}</th>
        </tr>
      </thead>
      <tbody>
        {count.lines.map((line) => {
          const difference = Number(line.actual_quantity) - Number(line.expected_quantity ?? "0");
          return (
            <tr key={line.id} className="border-t border-[var(--line)]">
              <td className="py-2">{line.name}</td>
              <td className="py-2 text-right">
                {formatQuantity(line.expected_quantity ?? "0")} {units(line.unit)}
              </td>
              <td className="py-2 text-right">
                {formatQuantity(line.actual_quantity)} {units(line.unit)}
              </td>
              <td
                className={cn(
                  "py-2 text-right",
                  difference < 0 ? "text-[var(--danger)]" : difference > 0 ? "text-emerald-700" : "",
                )}
              >
                {formatQuantity(String(difference))} {units(line.unit)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function InventoryCountsPanel() {
  const t = useTranslations("stock");
  const counts = useInventoryCounts();
  const closeCount = useCloseInventoryCount();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const [editing, setEditing] = useState<InventoryCount | null>(null);
  const [draft, setDraft] = useState<CountDraft | null>(null);
  const stock = useStockLevels(draft?.date ?? null);
  const currentUser = useCurrentUser();
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);

  const options = componentOptions(
    ingredients.list.data ?? [],
    semiProducts.list.data ?? [],
    "produced",
    t("ingredient"),
    t("semiProduct"),
  );

  const open = (row: InventoryCount | null) => {
    counts.save.reset();
    counts.remove.reset();
    closeCount.reset();
    setEditing(row);
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  const fillFromStock = () => {
    if (!draft) return;
    const present = new Set(draft.lines.map((line) => line.component));
    const extra: ComponentLineDraft[] = [];
    for (const row of stock.data ?? []) {
      if (!row.is_active) continue;
      const value = componentValue({ ingredient: row.ingredient, semi_product: row.semi_product });
      if (present.has(value)) continue;
      extra.push({ key: newDraftKey(), component: value, quantity: "", loss_percent: "0", unit_cost: "" });
    }
    setDraft({ ...draft, lines: [...draft.lines, ...extra] });
  };

  const body = (value: CountDraft) => ({
    date: value.date,
    comment: value.comment,
    lines: value.lines.map((line) => ({
      ...componentRef(line.component),
      actual_quantity: line.quantity.replace(",", "."),
      unit_cost: line.unit_cost.trim() === "" ? null : line.unit_cost.replace(",", "."),
    })),
  });

  const isClosed = editing?.status === "closed";

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.inventoryCounts")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
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
          title={editing === null ? t("newInventoryCount") : `${t("inventory.inventoryCounts")} · ${editing.date}`}
          pending={counts.save.isPending}
          error={counts.save.error ?? counts.remove.error ?? closeCount.error}
          submitLabel={isClosed ? null : t("saveDraft")}
          onSubmit={() =>
            counts.save.mutate(
              { id: editing ? editing.id : null, body: body(draft) },
              { onSuccess: (saved) => setEditing(saved) },
            )
          }
          onDelete={editing === null ? null : () => counts.remove.mutate(editing.id, { onSuccess: close })}
          deletePending={counts.remove.isPending}
        >
          {isClosed && editing ? (
            <ClosedCountView count={editing} />
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t("date")}>
                  <Input
                    type="date"
                    required
                    value={draft.date}
                    onChange={(event) => setDraft({ ...draft, date: event.target.value })}
                  />
                </Field>
                <div className="flex items-end">
                  <Button type="button" variant="outline" onClick={fillFromStock} disabled={!stock.data}>
                    {t("fillFromStock")}
                  </Button>
                </div>
                <Field label={t("comment")} className="sm:col-span-2">
                  <Textarea
                    value={draft.comment}
                    onChange={(event) => setDraft({ ...draft, comment: event.target.value })}
                  />
                </Field>
              </div>
              <CardTitle>{t("actualQuantities")}</CardTitle>
              <ComponentLinesEditor
                lines={draft.lines}
                onChange={(lines) => setDraft({ ...draft, lines })}
                options={options}
                extraColumn={isFinanceAdmin ? "unitCost" : null}
                quantityLabel={t("actual")}
              />
              {editing ? (
                <div className="flex flex-wrap items-center gap-3 rounded-2xl bg-[var(--cream)] p-4">
                  <p className="flex-1 text-sm text-[var(--ink)]">{t("closeCountHint")}</p>
                  <Button
                    type="button"
                    disabled={closeCount.isPending || counts.save.isPending}
                    onClick={() =>
                      counts.save.mutate(
                        { id: editing.id, body: body(draft) },
                        {
                          onSuccess: (saved) =>
                            closeCount.mutate(saved.id, { onSuccess: (closed) => setEditing(closed) }),
                        },
                      )
                    }
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
