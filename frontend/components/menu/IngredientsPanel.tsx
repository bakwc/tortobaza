"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
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
  formatMoney,
} from "@/components/menu/ui";
import { useIngredientCategories, useIngredients } from "@/hooks/useStock";
import type { Ingredient, IngredientBody, MenuUnit } from "@/lib/api/types";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

function emptyIngredient(): IngredientBody {
  return { name: "", category: null, unit: "g", is_active: true };
}

export function IngredientsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const ingredients = useIngredients();
  const categories = useIngredientCategories();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<IngredientBody | null>(null);
  const [newCategory, setNewCategory] = useState("");

  const open = (row: Ingredient | null) => {
    ingredients.save.reset();
    ingredients.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(
      row
        ? { name: row.name, category: row.category, unit: row.unit, is_active: row.is_active }
        : emptyIngredient(),
    );
  };

  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("menu.ingredients")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={ingredients.list.isLoading} isError={ingredients.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("category")}</th>
                <th className="py-2">{t("unit")}</th>
                <th className="py-2 text-right">{t("avgCost")}</th>
              </tr>
            </thead>
            <tbody>
              {(ingredients.list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className={row.is_active ? "py-2" : "py-2 text-[var(--muted-2)] line-through"}>
                    {row.name}
                  </td>
                  <td className="py-2">{row.category_name ?? "—"}</td>
                  <td className="py-2">{units(row.unit)}</td>
                  <td className="py-2 text-right">
                    {row.avg_cost !== undefined ? formatMoney(row.avg_cost) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </Card>

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
          onCancel={null}
          title={editingId === null ? t("newIngredient") : draft.name}
          pending={ingredients.save.isPending}
          error={ingredients.save.error ?? ingredients.remove.error}
          submitLabel={t("save")}
          onSubmit={() => ingredients.save.mutate({ id: editingId, body: draft }, { onSuccess: close })}
          onDelete={editingId === null ? null : () => ingredients.remove.mutate(editingId, { onSuccess: close })}
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
