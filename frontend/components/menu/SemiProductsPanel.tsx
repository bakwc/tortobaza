"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { MarkdownEditor } from "@/components/menu/MarkdownEditor";
import { MenuImages } from "@/components/menu/MenuImages";
import { RecipeView } from "@/components/menu/RecipeView";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  ComponentLinesEditor,
  componentOptions,
  draftFromLine,
  linesToBody,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
import { EditorDialog } from "@/components/menu/EditorDialog";
import {
  Card,
  CardTitle,
  CheckboxField,
  Field,
  NativeSelect,
  QueryState,
  formatMoney,
  formatQuantity,
} from "@/components/menu/ui";
import { useIngredients, useSemiProductImages, useSemiProducts } from "@/hooks/useStock";
import type { MenuUnit, SemiProduct } from "@/lib/api/types";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

type SemiDraft = {
  name: string;
  unit: MenuUnit;
  yield_quantity: string;
  is_produced: boolean;
  is_active: boolean;
  method: string;
  lines: ComponentLineDraft[];
};

function draftFrom(row: SemiProduct | null): SemiDraft {
  if (row === null) {
    return { name: "", unit: "g", yield_quantity: "", is_produced: false, is_active: true, method: "", lines: [] };
  }
  return {
    name: row.name,
    unit: row.unit,
    yield_quantity: row.yield_quantity,
    is_produced: row.is_produced,
    is_active: row.is_active,
    method: row.method,
    lines: row.lines.map(draftFromLine),
  };
}

export function SemiProductsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const semiProducts = useSemiProducts();
  const images = useSemiProductImages();
  const ingredients = useIngredients();
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [viewing, setViewing] = useState<SemiProduct | null>(null);
  const [draft, setDraft] = useState<SemiDraft | null>(null);
  const current =
    viewing === null ? null : (semiProducts.list.data ?? []).find((row) => row.id === viewing.id) ?? viewing;

  const openView = (row: SemiProduct) => {
    semiProducts.save.reset();
    semiProducts.remove.reset();
    setViewing(row);
    setDraft(null);
    setMode("view");
  };
  const openNew = () => {
    semiProducts.save.reset();
    semiProducts.remove.reset();
    setViewing(null);
    setDraft(draftFrom(null));
    setMode("edit");
  };
  const openEdit = () => {
    if (current === null) return;
    setDraft(draftFrom(current));
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

  const options = componentOptions(
    ingredients.list.data ?? [],
    (semiProducts.list.data ?? []).filter((row) => viewing === null || row.id !== viewing.id),
    "all",
    t("ingredient"),
    t("semiProduct"),
  );

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("menu.semiProducts")}</CardTitle>
          <Button type="button" size="sm" onClick={openNew}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={semiProducts.list.isLoading} isError={semiProducts.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("yield")}</th>
                <th className="py-2">{t("producedInAdvance")}</th>
                <th className="py-2 text-right">{t("avgCost")}</th>
              </tr>
            </thead>
            <tbody>
              {(semiProducts.list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => openView(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className={row.is_active ? "py-2" : "py-2 text-[var(--muted-2)] line-through"}>
                    {row.name}
                  </td>
                  <td className="py-2">
                    {formatQuantity(row.yield_quantity)} {units(row.unit)}
                  </td>
                  <td className="py-2">{row.is_produced ? t("yes") : t("no")}</td>
                  <td className="py-2 text-right">
                    {row.avg_cost !== undefined && row.is_produced ? formatMoney(row.avg_cost) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </Card>

      {mode === "view" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <RecipeView
              title={current.name}
              badges={[
                `${formatQuantity(current.yield_quantity)} ${units(current.unit)}`,
                current.is_produced ? t("producedInAdvance") : "",
                current.is_active ? "" : t("inactive"),
                current.avg_cost !== undefined && current.is_produced
                  ? `${t("avgCost")}: ${formatMoney(current.avg_cost)}`
                  : "",
              ].filter((badge) => badge !== "")}
              images={current.images}
              compositionTitle={t("composition")}
              lines={current.lines}
              sections={[]}
              method={current.method}
              onEdit={openEdit}
            >
              {null}
            </RecipeView>
          </DialogContent>
        </Dialog>
      ) : null}

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : cancelEdit())}
          title={viewing === null ? t("newSemiProduct") : draft.name}
          pending={semiProducts.save.isPending}
          error={semiProducts.save.error ?? semiProducts.remove.error}
          submitLabel={t("save")}
          onSubmit={() =>
            semiProducts.save.mutate(
              {
                id: viewing === null ? null : viewing.id,
                body: {
                  name: draft.name,
                  unit: draft.unit,
                  yield_quantity: draft.yield_quantity.replace(",", "."),
                  is_produced: draft.is_produced,
                  is_active: draft.is_active,
                  method: draft.method,
                  lines: linesToBody(draft.lines),
                },
              },
              {
                onSuccess: (saved) => {
                  setViewing(saved);
                  setDraft(null);
                  setMode("view");
                },
              },
            )
          }
          onCancel={cancelEdit}
          onDelete={viewing === null ? null : () => semiProducts.remove.mutate(viewing.id, { onSuccess: close })}
          deletePending={semiProducts.remove.isPending}
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={t("name")} className="sm:col-span-3">
              <Input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            </Field>
            <Field label={t("yield")}>
              <Input
                required
                inputMode="decimal"
                value={draft.yield_quantity}
                onChange={(event) => setDraft({ ...draft, yield_quantity: event.target.value })}
              />
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
            <div className="flex flex-col justify-end gap-2 pb-1">
              <CheckboxField
                label={t("producedInAdvance")}
                checked={draft.is_produced}
                onChange={(value) => setDraft({ ...draft, is_produced: value })}
              />
              <CheckboxField
                label={t("isActive")}
                checked={draft.is_active}
                onChange={(value) => setDraft({ ...draft, is_active: value })}
              />
            </div>
          </div>
          <p className="text-xs text-[var(--muted-2)]">{t("producedInAdvanceHint")}</p>
          <Field label={t("method")}>
            <MarkdownEditor value={draft.method} onChange={(method) => setDraft({ ...draft, method })} />
          </Field>
          {viewing !== null ? (
            <MenuImages
              images={(semiProducts.list.data ?? []).find((row) => row.id === viewing.id)?.images ?? viewing.images}
              pending={images.upload.isPending || images.remove.isPending}
              onUpload={(file) => images.upload.mutate({ id: viewing.id, file })}
              onDelete={(imageId) => images.remove.mutate({ id: viewing.id, imageId })}
            />
          ) : null}
          <CardTitle>{t("composition")}</CardTitle>
          <ComponentLinesEditor
            lines={draft.lines}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={options}
            extraColumn="loss"
            quantityLabel={t("quantity")}
          />
        </EditorDialog>
      ) : null}
    </div>
  );
}
