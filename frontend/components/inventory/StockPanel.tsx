"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Card, CardTitle, Field, QueryState, formatMoney, formatQuantity } from "@/components/menu/ui";
import { useStockLevels, useStockMovements } from "@/hooks/useStock";
import type { StockRow } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function MovementsDialog({ row, onClose }: { row: StockRow; onClose: () => void }) {
  const t = useTranslations("stock");
  const kinds = useTranslations("stock.movementKinds");
  const units = useTranslations("stock.units");
  const movements = useStockMovements({ ingredient: row.ingredient, semi_product: row.semi_product });
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
  const [selected, setSelected] = useState<StockRow | null>(null);
  const stock = useStockLevels(date === "" ? null : date);
  const rows = (stock.data ?? []).filter((row) => row.is_active || Number(row.quantity) !== 0);
  const hasCosts = rows.some((row) => row.value !== undefined);
  const totalValue = rows.reduce((sum, row) => sum + Number(row.value ?? "0"), 0);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <CardTitle>{t("inventory.stock")}</CardTitle>
          <Field label={t("onDate")}>
            <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </Field>
        </div>
        <QueryState isLoading={stock.isLoading} isError={stock.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("category")}</th>
                <th className="py-2 text-right">{t("remaining")}</th>
                {hasCosts ? <th className="py-2 text-right">{t("avgCost")}</th> : null}
                {hasCosts ? <th className="py-2 text-right">{t("value")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.ingredient ?? "s"}-${row.semi_product ?? "i"}`}
                  onClick={() => setSelected(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className="py-2">{row.name}</td>
                  <td className="py-2">{row.semi_product !== null ? t("semiProduct") : (row.category_name ?? "—")}</td>
                  <td className={cn("py-2 text-right", Number(row.quantity) < 0 ? "text-[var(--danger)]" : "")}>
                    {formatQuantity(row.quantity)} {units(row.unit)}
                  </td>
                  {hasCosts ? <td className="py-2 text-right">{formatMoney(row.avg_cost ?? "0")}</td> : null}
                  {hasCosts ? <td className="py-2 text-right">{formatMoney(row.value ?? "0")}</td> : null}
                </tr>
              ))}
            </tbody>
            {hasCosts ? (
              <tfoot>
                <tr className="border-t border-[var(--line)] font-semibold">
                  <td className="py-2" colSpan={4}>
                    {t("total")}
                  </td>
                  <td className="py-2 text-right">{formatMoney(String(totalValue))}</td>
                </tr>
              </tfoot>
            ) : null}
          </table>
        </QueryState>
      </Card>
      {selected ? <MovementsDialog row={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
