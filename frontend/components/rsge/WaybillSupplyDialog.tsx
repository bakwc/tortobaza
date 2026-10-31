"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { QueryState, formatQuantity } from "@/components/menu/ui";
import { WaybillIngredientDialog } from "@/components/rsge/WaybillIngredientDialog";
import { WaybillLinePicker } from "@/components/rsge/WaybillLinePicker";
import { useCreateWaybillSupply, useWaybillSupplyDraft } from "@/hooks/useWaybills";
import { useIngredients } from "@/hooks/useStock";
import { formatMoney } from "@/lib/format";
import type { MenuUnit, RsWaybill, WaybillSupplyDraftLine } from "@/lib/api/types";

type RowDraft = {
  goodId: number;
  ingredient: string;
  quantity: string;
  skipped: boolean;
};

type CreatingIngredient = {
  goodId: number;
  name: string;
  unit: MenuUnit;
  quantity: string | null;
};

function localized(locale: string, original: string, ru: string): string {
  if (locale === "ru" && ru !== "") return ru;
  return original;
}

function scaledQuantity(quantity: string, factor: string): string {
  const product = Number(quantity) * Number(factor);
  return String(Math.round(product * 1000) / 1000);
}

function seedRows(lines: WaybillSupplyDraftLine[]): RowDraft[] {
  return lines.map((line) => {
    if (line.alias !== null && line.alias.ignored) {
      return { goodId: line.good_id, ingredient: "", quantity: "", skipped: true };
    }
    if (line.alias !== null && line.alias.ingredient_id !== null && line.alias.factor !== null) {
      return {
        goodId: line.good_id,
        ingredient: String(line.alias.ingredient_id),
        quantity: scaledQuantity(line.quantity, line.alias.factor),
        skipped: false,
      };
    }
    return { goodId: line.good_id, ingredient: "", quantity: "", skipped: false };
  });
}

export function WaybillSupplyDialog({ waybill, onClose }: { waybill: RsWaybill; onClose: () => void }) {
  const t = useTranslations("rsge");
  const units = useTranslations("stock.units");
  const locale = useLocale();
  const draft = useWaybillSupplyDraft(waybill.id);
  const create = useCreateWaybillSupply();
  const ingredients = useIngredients();
  const [rows, setRows] = useState<RowDraft[] | null>(null);
  const [creating, setCreating] = useState<CreatingIngredient | null>(null);
  if (draft.data !== undefined && rows === null) {
    setRows(seedRows(draft.data.lines));
  }

  function updateRow(goodId: number, patch: Partial<RowDraft>) {
    setRows((current) => {
      if (current === null) return current;
      return current.map((row) => (row.goodId === goodId ? { ...row, ...patch } : row));
    });
  }

  function submit() {
    if (rows === null) return;
    create.mutate(
      {
        id: waybill.id,
        body: {
          lines: rows.map((row) => ({
            good_id: row.goodId,
            ingredient: row.skipped || row.ingredient === "" ? null : Number(row.ingredient),
            quantity: row.skipped || row.quantity === "" ? null : row.quantity,
            skipped: row.skipped,
          })),
        },
      },
      { onSuccess: onClose },
    );
  }

  const ready = draft.data !== undefined && rows !== null;
  const supplierLabel =
    draft.data === undefined
      ? ""
      : draft.data.supplier === null
        ? draft.data.supplier_name
        : draft.data.supplier.name;

  return (
    <>
      <EditorDialog
        open
        onOpenChange={(open) => {
          if (!open && creating === null) onClose();
        }}
        title={t("supplyTitle")}
        pending={create.isPending}
        error={create.error}
        onSubmit={submit}
        onCancel={onClose}
        onDelete={null}
        deletePending={false}
        submitLabel={ready ? t("createSupply") : null}
        headerAction={null}
        below={null}
      >
        <p className="text-sm text-[var(--ink)]">
          <span className="font-medium">{localized(locale, waybill.seller_name, waybill.seller_name_ru)}</span>
          <span className="mx-1.5 text-[var(--ink)]/40">·</span>
          <span>{waybill.waybill_number}</span>
          {supplierLabel !== "" ? (
            <>
              <span className="mx-1.5 text-[var(--ink)]/40">·</span>
              <span>{supplierLabel}</span>
            </>
          ) : null}
          {draft.data !== undefined ? (
            <>
              <span className="mx-1.5 text-[var(--ink)]/40">·</span>
              <span>{draft.data.date}</span>
            </>
          ) : null}
        </p>
        <QueryState isLoading={draft.isLoading} isError={draft.isError}>
          {draft.data !== undefined && rows !== null ? (
            <div className="grid gap-4">
              {draft.data.lines.map((line) => {
                const row = rows.find((item) => item.goodId === line.good_id);
                if (row === undefined) return null;
                const ingredient = (ingredients.list.data ?? []).find((item) => String(item.id) === row.ingredient);
                const name = localized(locale, line.name, line.name_ru);
                return (
                  <div key={line.good_id} className="grid gap-2 border-t border-[var(--line)] pt-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="font-medium text-[var(--ink)]">{name}</p>
                      <p className="text-sm text-[var(--muted-2)]">
                        {formatQuantity(line.quantity)} {localized(locale, line.unit_txt, line.unit_txt_ru)}
                        <span className="mx-1.5">·</span>
                        {formatMoney(line.amount, "GEL")}
                      </p>
                    </div>
                    <div className={row.skipped ? "grid gap-2" : "grid gap-2 sm:grid-cols-[1fr_9rem]"}>
                      <WaybillLinePicker
                        line={line}
                        ingredientId={row.ingredient}
                        skipped={row.skipped}
                        ingredients={ingredients.list.data ?? []}
                        onSkip={() =>
                          updateRow(line.good_id, { skipped: true, ingredient: "", quantity: "" })
                        }
                        onPick={(ingredientId, quantity) =>
                          updateRow(
                            line.good_id,
                            quantity === null
                              ? { ingredient: ingredientId, skipped: false }
                              : { ingredient: ingredientId, quantity, skipped: false },
                          )
                        }
                        onCreate={(createName, unit, quantity) =>
                          setCreating({ goodId: line.good_id, name: createName, unit, quantity })
                        }
                      />
                      {row.skipped ? null : (
                        <div className="relative">
                          <Input
                            required
                            inputMode="decimal"
                            placeholder={t("quantity")}
                            value={row.quantity}
                            onChange={(event) => updateRow(line.good_id, { quantity: event.target.value })}
                            className="pr-12"
                          />
                          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                            {ingredient ? units(ingredient.unit) : ""}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </QueryState>
      </EditorDialog>
      {creating === null ? null : (
        <WaybillIngredientDialog
          name={creating.name}
          unit={creating.unit}
          onClose={() => setCreating(null)}
          onCreated={(id, unit) => {
            updateRow(
              creating.goodId,
              creating.quantity !== null && unit === creating.unit
                ? { ingredient: String(id), quantity: creating.quantity, skipped: false }
                : { ingredient: String(id), skipped: false },
            );
            setCreating(null);
          }}
        />
      )}
    </>
  );
}
