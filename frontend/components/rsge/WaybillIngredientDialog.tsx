"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Field, NativeSelect } from "@/components/menu/ui";
import { useIngredientCategories, useIngredients } from "@/hooks/useStock";
import type { IngredientBody, MenuUnit } from "@/lib/api/types";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

export function WaybillIngredientDialog({
  name,
  unit,
  onClose,
  onCreated,
}: {
  name: string;
  unit: MenuUnit;
  onClose: () => void;
  onCreated: (id: number, unit: MenuUnit) => void;
}) {
  const t = useTranslations("rsge");
  const stock = useTranslations("stock");
  const units = useTranslations("stock.units");
  const ingredients = useIngredients();
  const categories = useIngredientCategories();
  const [draftName, setDraftName] = useState(name);
  const [draftUnit, setDraftUnit] = useState<MenuUnit>(unit);
  const [category, setCategory] = useState<number | null>(null);
  const [gramsPerUnit, setGramsPerUnit] = useState("");

  function submit() {
    const body: IngredientBody = {
      name: draftName.trim(),
      category,
      unit: draftUnit,
      is_active: true,
      avg_cost: null,
      cost_quantity: null,
      grams_per_unit: draftUnit === "g" ? null : gramsPerUnit,
      sale_price: null,
    };
    Reflect.deleteProperty(body, "avg_cost");
    Reflect.deleteProperty(body, "cost_quantity");
    Reflect.deleteProperty(body, "sale_price");
    if (draftUnit === "g") Reflect.deleteProperty(body, "grams_per_unit");
    ingredients.save.mutate({ id: null, body }, { onSuccess: (created) => onCreated(created.id, draftUnit) });
  }

  return (
    <EditorDialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={t("newIngredientTitle")}
      pending={ingredients.save.isPending}
      error={ingredients.save.error}
      onSubmit={submit}
      onCancel={onClose}
      onDelete={null}
      deletePending={false}
      submitLabel={stock("createIngredient")}
      headerAction={null}
      below={null}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={stock("name")} className="sm:col-span-2">
          <Input required value={draftName} onChange={(event) => setDraftName(event.target.value)} />
        </Field>
        <Field label={stock("category")}>
          <NativeSelect
            value={category ?? ""}
            onChange={(event) => setCategory(event.target.value === "" ? null : Number(event.target.value))}
          >
            <option value="">—</option>
            {(categories.list.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label={stock("unit")}>
          <NativeSelect
            value={draftUnit}
            onChange={(event) => {
              const next = event.target.value as MenuUnit;
              setDraftUnit(next);
              if (next === "g") setGramsPerUnit("");
            }}
          >
            {UNITS.map((item) => (
              <option key={item} value={item}>
                {units(item)}
              </option>
            ))}
          </NativeSelect>
        </Field>
        {draftUnit === "g" ? null : (
          <Field label={stock(draftUnit === "ml" ? "density" : "pieceWeight")} className="sm:col-span-2">
            <Input
              required
              inputMode="decimal"
              value={gramsPerUnit}
              onChange={(event) => setGramsPerUnit(event.target.value)}
            />
          </Field>
        )}
      </div>
    </EditorDialog>
  );
}
