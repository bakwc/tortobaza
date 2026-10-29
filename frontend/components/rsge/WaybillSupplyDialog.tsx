"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { CheckboxField, ErrorText, NativeSelect, QueryState, formatQuantity } from "@/components/menu/ui";
import { useCreateWaybillSupply, useWaybillSupplyDraft } from "@/hooks/useWaybills";
import { useIngredients } from "@/hooks/useStock";
import { formatMoney } from "@/lib/format";
import type { IngredientBody, MenuUnit, RsWaybill, WaybillSupplyDraftLine } from "@/lib/api/types";

type RowDraft = {
  goodId: number;
  ingredient: string;
  quantity: string;
  skipped: boolean;
  createName: string;
  createUnit: MenuUnit;
  gramsPerUnit: string;
};

function localized(locale: string, original: string, ru: string): string {
  if (locale === "ru" && ru !== "") return ru;
  return original;
}

function scaledQuantity(quantity: string, factor: string): string {
  const product = Number(quantity) * Number(factor);
  return String(Math.round(product * 1000) / 1000);
}

function seedRows(lines: WaybillSupplyDraftLine[], locale: string): RowDraft[] {
  return lines.map((line) => {
    const suggestion = line.suggestions[0];
    const createUnit = suggestion === undefined ? "g" : suggestion.unit;
    const createName = localized(locale, line.name, line.name_ru);
    if (line.alias !== null && line.alias.ignored) {
      return {
        goodId: line.good_id,
        ingredient: "",
        quantity: "",
        skipped: true,
        createName,
        createUnit,
        gramsPerUnit: "",
      };
    }
    if (line.alias !== null && line.alias.ingredient_id !== null && line.alias.factor !== null) {
      return {
        goodId: line.good_id,
        ingredient: String(line.alias.ingredient_id),
        quantity: scaledQuantity(line.quantity, line.alias.factor),
        skipped: false,
        createName,
        createUnit,
        gramsPerUnit: "",
      };
    }
    return {
      goodId: line.good_id,
      ingredient: "",
      quantity: "",
      skipped: false,
      createName,
      createUnit,
      gramsPerUnit: "",
    };
  });
}

export function WaybillSupplyDialog({ waybill, onClose }: { waybill: RsWaybill; onClose: () => void }) {
  const t = useTranslations("rsge");
  const units = useTranslations("stock.units");
  const stock = useTranslations("stock");
  const locale = useLocale();
  const draft = useWaybillSupplyDraft(waybill.id);
  const create = useCreateWaybillSupply();
  const ingredients = useIngredients();
  const [rows, setRows] = useState<RowDraft[] | null>(null);
  if (draft.data !== undefined && rows === null) {
    setRows(seedRows(draft.data.lines, locale));
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
    <EditorDialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
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
                  <CheckboxField
                    label={t("skipLine")}
                    checked={row.skipped}
                    onChange={(skipped) =>
                      updateRow(
                        line.good_id,
                        skipped ? { skipped, ingredient: "", quantity: "" } : { skipped },
                      )
                    }
                  />
                  {row.skipped ? null : (
                    <>
                      <div className="grid gap-2 sm:grid-cols-[1fr_9rem]">
                        <SearchSelect
                          options={(ingredients.list.data ?? [])
                            .filter((item) => item.is_active || String(item.id) === row.ingredient)
                            .map((item) => ({ value: String(item.id), label: item.name }))}
                          value={row.ingredient}
                          onChange={(ingredientId) => updateRow(line.good_id, { ingredient: ingredientId })}
                          placeholder={stock("chooseComponent")}
                          required={true}
                          className="min-w-0"
                        />
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
                      </div>
                      {line.suggestions.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {line.suggestions.map((suggestion) => {
                            if (suggestion.ingredient_id === null) return null;
                            const match = (ingredients.list.data ?? []).find(
                              (item) => item.id === suggestion.ingredient_id,
                            );
                            if (match === undefined) return null;
                            const quantity = scaledQuantity(line.quantity, suggestion.factor);
                            return (
                              <Button
                                key={`${suggestion.ingredient_id}-${suggestion.factor}`}
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  updateRow(line.good_id, {
                                    ingredient: String(match.id),
                                    quantity,
                                  })
                                }
                              >
                                {match.name} · {formatQuantity(quantity)} {units(match.unit)}
                              </Button>
                            );
                          })}
                        </div>
                      ) : null}
                      {row.ingredient === "" ? (
                        <div className="flex flex-wrap items-end gap-2">
                          <Input
                            value={row.createName}
                            onChange={(event) => updateRow(line.good_id, { createName: event.target.value })}
                            placeholder={t("name")}
                            className="h-9 min-w-48 flex-1"
                          />
                          <NativeSelect
                            value={row.createUnit}
                            onChange={(event) =>
                              updateRow(line.good_id, { createUnit: event.target.value as MenuUnit })
                            }
                            className="h-9 w-28 px-4"
                          >
                            <option value="g">{units("g")}</option>
                            <option value="ml">{units("ml")}</option>
                            <option value="pcs">{units("pcs")}</option>
                          </NativeSelect>
                          {row.createUnit === "g" ? null : (
                            <Input
                              required
                              inputMode="decimal"
                              placeholder={t("gramsPerUnit")}
                              value={row.gramsPerUnit}
                              onChange={(event) => updateRow(line.good_id, { gramsPerUnit: event.target.value })}
                              className="h-9 w-40"
                            />
                          )}
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={
                              ingredients.save.isPending ||
                              row.createName.trim() === "" ||
                              (row.createUnit !== "g" && row.gramsPerUnit.trim() === "")
                            }
                            onClick={() => {
                              const body: IngredientBody = {
                                name: row.createName.trim(),
                                category: null,
                                unit: row.createUnit,
                                is_active: true,
                                avg_cost: null,
                                cost_quantity: null,
                                grams_per_unit: row.createUnit === "g" ? null : row.gramsPerUnit,
                                sale_price: null,
                              };
                              Reflect.deleteProperty(body, "avg_cost");
                              Reflect.deleteProperty(body, "cost_quantity");
                              Reflect.deleteProperty(body, "sale_price");
                              if (row.createUnit === "g") Reflect.deleteProperty(body, "grams_per_unit");
                              ingredients.save.mutate(
                                { id: null, body },
                                {
                                  onSuccess: (created) =>
                                    updateRow(line.good_id, { ingredient: String(created.id) }),
                                },
                              );
                            }}
                          >
                            {stock("createIngredient")}
                          </Button>
                        </div>
                      ) : null}
                    </>
                  )}
                </div>
              );
            })}
            <ErrorText error={ingredients.save.error} />
          </div>
        ) : null}
      </QueryState>
    </EditorDialog>
  );
}
