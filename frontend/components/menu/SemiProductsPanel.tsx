"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Check, ChefHat, ChevronRight, Layers, Package, Plus, Search } from "lucide-react";
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
import { cn } from "@/lib/utils";

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

function SemiProductRow({
  row,
  yieldLabel,
  onOpen,
}: {
  row: SemiProduct;
  yieldLabel: string;
  onOpen: () => void;
}) {
  const t = useTranslations("stock");
  const cover = row.images[0];
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        "group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--cream-soft)] focus-visible:bg-[var(--cream-soft)] focus-visible:outline-none",
        !row.is_active && "opacity-60",
      )}
    >
      {cover ? (
        <img
          src={cover.image.src}
          srcSet={cover.image.srcset}
          sizes="44px"
          alt=""
          loading="lazy"
          className={cn(
            "h-11 w-11 shrink-0 rounded-xl border border-[var(--line)] object-cover",
            !row.is_active && "grayscale",
          )}
        />
      ) : (
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--brand)]/10 text-[var(--brand)]">
          <ChefHat className="h-5 w-5" />
        </span>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={cn("font-semibold text-[var(--ink)]", !row.is_active && "line-through")}>{row.name}</p>
          {row.is_active ? null : (
            <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-[11px] font-semibold text-[var(--muted-2)]">
              {t("inactive")}
            </span>
          )}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[var(--muted-2)]">
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" />
            {t("componentsCount", { count: row.lines.length })}
          </span>
        </div>
      </div>
      <span className="hidden shrink-0 items-center gap-1 rounded-full bg-[var(--cream)] px-2.5 py-1 text-xs font-semibold text-[var(--ink)] sm:flex">
        {yieldLabel}
      </span>
      {row.avg_cost !== undefined && row.is_produced ? (
        <span className="w-24 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
          {formatMoney(row.avg_cost)}
        </span>
      ) : null}
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </button>
  );
}

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
  const [search, setSearch] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
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
  const rows = semiProducts.list.data ?? [];
  const query = search.trim().toLowerCase();
  const allGroups = [
    { key: "produced", label: t("producedInAdvance"), rows: rows.filter((row) => row.is_produced) },
    { key: "order", label: t("madeToOrder"), rows: rows.filter((row) => !row.is_produced) },
  ].filter((group) => group.rows.length > 0);
  const groups = allGroups
    .filter((group) => groupFilter === "all" || group.key === groupFilter)
    .map((group) => ({ ...group, rows: group.rows.filter((row) => row.name.toLowerCase().includes(query)) }))
    .filter((group) => group.rows.length > 0);
  const activeCount = rows.filter((row) => row.is_active).length;

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--ink)]">{t("menu.semiProducts")}</h2>
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
              onClick={() => setGroupFilter(chip.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                groupFilter === chip.key
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {chip.label}
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px]",
                  groupFilter === chip.key ? "bg-white/25" : "bg-[var(--cream)]",
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

      <QueryState isLoading={semiProducts.list.isLoading} isError={semiProducts.list.isError}>
        {groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
            <ChefHat className="h-12 w-12 text-[var(--muted)]" />
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
                    <SemiProductRow
                      key={row.id}
                      row={row}
                      yieldLabel={`${formatQuantity(row.yield_quantity)} ${units(row.unit)}`}
                      onOpen={() => openView(row)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryState>

      {mode === "view" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <RecipeView
              title={current.name}
              badges={[
                current.is_produced ? t("producedInAdvance") : "",
                current.is_active ? "" : t("inactive"),
              ].filter((badge) => badge !== "")}
              stats={[
                { label: t("yield"), value: `${formatQuantity(current.yield_quantity)} ${units(current.unit)}` },
                { label: t("componentsLabel"), value: String(current.lines.length) },
                ...(current.avg_cost !== undefined && current.is_produced
                  ? [{ label: t("avgCost"), value: formatMoney(current.avg_cost) }]
                  : []),
              ]}
              images={current.images}
              compositionTitle={t("composition")}
              lines={current.lines}
              sections={[]}
              method={current.method}
              onEdit={openEdit}
              printHref={null}
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
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{t("method")}</span>
            <MarkdownEditor value={draft.method} onChange={(method) => setDraft({ ...draft, method })} />
          </div>
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
