"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Check, ChefHat, ChevronRight, Layers, Package, Plus, Search, Trash2 } from "lucide-react";
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
import { useCan } from "@/hooks/useAuth";
import {
  Card,
  CardTitle,
  CheckboxField,
  ErrorText,
  Field,
  GroupSelect,
  NativeSelect,
  QueryState,
  formatQuantity,
  formatUnitCost,
} from "@/components/menu/ui";
import { useIngredients, useSemiProductCategories, useSemiProductImages, useSemiProducts } from "@/hooks/useStock";
import { useRouter } from "@/i18n/navigation";
import type { IngredientBody, MenuUnit, SemiProduct } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const UNITS: MenuUnit[] = ["g", "ml", "pcs"];

function costPerYieldUnit(cost: string, yieldQuantity: string): string {
  return (Number(cost) / Number(yieldQuantity)).toFixed(6);
}

type SemiDraft = {
  name: string;
  category: number | null;
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
  selecting,
  selected,
  onOpen,
}: {
  row: SemiProduct;
  yieldLabel: string;
  selecting: boolean;
  selected: boolean;
  onOpen: () => void;
}) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const cover = row.images[0];
  return (
    <button
      type="button"
      aria-pressed={selecting ? selected : undefined}
      onClick={onOpen}
      className={cn(
        "group flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--cream-soft)] focus-visible:bg-[var(--cream-soft)] focus-visible:outline-none",
        !row.is_active && "opacity-60",
        selecting && selected && "bg-[var(--cream-soft)]",
      )}
    >
      {selecting ? (
        <span
          aria-hidden
          className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded border",
            selected ? "border-[var(--brand)] bg-[var(--brand)] text-white" : "border-[var(--line)] bg-white",
          )}
        >
          {selected ? <Check className="h-3.5 w-3.5" /> : null}
        </span>
      ) : null}
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
          {row.is_produced ? (
            <span className="rounded-full bg-[var(--cream)] px-2 py-0.5 text-[11px] font-semibold text-[var(--muted-2)]">
              {t("producedInAdvance")}
            </span>
          ) : null}
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
      {row.cost !== undefined ? (
        <span className="shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
          {formatUnitCost(costPerYieldUnit(row.cost, row.yield_quantity))}
          <span className="block text-[11px] font-normal text-[var(--muted-2)]">
            {t("costPerUnit", { unit: units(row.unit) })}
          </span>
        </span>
      ) : null}
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </button>
  );
}

function draftFrom(row: SemiProduct | null): SemiDraft {
  if (row === null) {
    return {
      name: "",
      category: null,
      unit: "g",
      yield_quantity: "",
      is_produced: false,
      is_active: true,
      method: "",
      lines: [],
    };
  }
  return {
    name: row.name,
    category: row.category,
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
  const canEdit = useCan("edit_menu");
  const units = useTranslations("stock.units");
  const router = useRouter();
  const searchParams = useSearchParams();
  const semiProducts = useSemiProducts();
  const categories = useSemiProductCategories();
  const images = useSemiProductImages();
  const ingredients = useIngredients();
  const semiParam = searchParams.get("semi");
  const paramId = semiParam === null ? null : Number(semiParam);
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [viewing, setViewing] = useState<SemiProduct | null>(null);
  const [ignoreSemiParam, setIgnoreSemiParam] = useState(false);
  const [draft, setDraft] = useState<SemiDraft | null>(null);
  const [newCategory, setNewCategory] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [assignCategory, setAssignCategory] = useState("");
  const requestedId = ignoreSemiParam
    ? viewing === null
      ? null
      : viewing.id
    : viewing !== null
      ? viewing.id
      : paramId !== null && Number.isFinite(paramId)
        ? paramId
        : null;
  const current =
    requestedId === null
      ? null
      : ((semiProducts.list.data ?? []).find((row) => row.id === requestedId) ??
        (viewing !== null && viewing.id === requestedId ? viewing : null));

  useEffect(() => {
    if (ignoreSemiParam && semiParam === null) setIgnoreSemiParam(false);
  }, [ignoreSemiParam, semiParam]);

  const openView = (row: SemiProduct) => {
    semiProducts.save.reset();
    semiProducts.remove.reset();
    setIgnoreSemiParam(false);
    setViewing(row);
    setDraft(null);
    setMode("view");
    router.replace(`/menu/semi-products?semi=${row.id}`, { scroll: false });
  };
  const openNew = () => {
    semiProducts.save.reset();
    semiProducts.remove.reset();
    setIgnoreSemiParam(true);
    setViewing(null);
    setDraft(draftFrom(null));
    setMode("edit");
    router.replace("/menu/semi-products", { scroll: false });
  };
  const openEdit = () => {
    if (current === null) return;
    setDraft(draftFrom(current));
    setMode("edit");
  };
  const close = () => {
    setMode(null);
    setDraft(null);
    setIgnoreSemiParam(true);
    setViewing(null);
    router.replace("/menu/semi-products", { scroll: false });
  };
  const cancelEdit = () => {
    setDraft(null);
    if (current === null) close();
    else setMode("view");
  };
  const selectIngredient = (lineKey: string, id: number) => {
    setDraft((currentDraft) =>
      currentDraft === null
        ? currentDraft
        : {
            ...currentDraft,
            lines: currentDraft.lines.map((line) =>
              line.key === lineKey ? { ...line, component: `ingredient:${id}`, suggestion: null } : line,
            ),
          },
    );
  };
  const createIngredient = (line: ComponentLineDraft, name: string, unit: MenuUnit) => {
    const trimmed = name.trim();
    if (trimmed === "") return;
    const existing = (ingredients.list.data ?? []).find((row) => row.name.toLowerCase() === trimmed.toLowerCase());
    if (existing !== undefined) {
      selectIngredient(line.key, existing.id);
      return;
    }
    const body: IngredientBody = {
      name: trimmed,
      category: null,
      unit,
      is_active: true,
      avg_cost: null,
      cost_quantity: null,
      grams_per_unit: unit === "ml" ? "1" : null,
      sale_price: null,
    };
    Reflect.deleteProperty(body, "avg_cost");
    Reflect.deleteProperty(body, "cost_quantity");
    Reflect.deleteProperty(body, "sale_price");
    if (unit !== "ml") Reflect.deleteProperty(body, "grams_per_unit");
    ingredients.save.mutate({ id: null, body }, { onSuccess: (created) => selectIngredient(line.key, created.id) });
  };
  const toggleSelecting = () => {
    setSelecting((value) => !value);
    setSelected([]);
    setAssignCategory("");
    semiProducts.assignCategory.reset();
  };
  const toggleSelected = (id: number) => {
    setSelected((currentIds) =>
      currentIds.includes(id) ? currentIds.filter((item) => item !== id) : [...currentIds, id],
    );
  };
  const setGroupSelected = (ids: number[], checked: boolean) => {
    setSelected((currentIds) => {
      if (checked) return [...new Set([...currentIds, ...ids])];
      const drop = new Set(ids);
      return currentIds.filter((id) => !drop.has(id));
    });
  };
  const [assignError, setAssignError] = useState(false);
  const assignSelected = () => {
    if (assignCategory === "") {
      setAssignError(true);
      return;
    }
    setAssignError(false);
    semiProducts.assignCategory.mutate(
      { ids: selected, category: assignCategory === "none" ? null : Number(assignCategory) },
      { onSuccess: () => setSelected([]) },
    );
  };

  const options = componentOptions(
    ingredients.list.data ?? [],
    (semiProducts.list.data ?? []).filter((row) => current === null || row.id !== current.id),
    "all",
    t("ingredient"),
    t("semiProduct"),
  );
  const rows = semiProducts.list.data ?? [];
  const query = search.trim().toLowerCase();
  const allGroups = [
    ...(categories.list.data ?? []).map((category) => ({
      key: String(category.id),
      label: category.name,
      rows: rows.filter((row) => row.category === category.id),
    })),
    { key: "none", label: t("noCategory"), rows: rows.filter((row) => row.category === null) },
  ].filter((group) => group.rows.length > 0);
  const groups = allGroups
    .filter((group) => categoryFilter === "all" || group.key === categoryFilter)
    .map((group) => ({ ...group, rows: group.rows.filter((row) => row.name.toLowerCase().includes(query)) }))
    .filter((group) => group.rows.length > 0);
  const activeCount = rows.filter((row) => row.is_active).length;

  return (
    <div className={cn("grid gap-6", selected.length > 0 && "pb-28")}>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--ink)]">{t("menu.semiProducts")}</h2>
          <div className="flex flex-wrap items-center gap-2">
            {canEdit ? (
            <Button type="button" variant={selecting ? "primary" : "outline"} onClick={toggleSelecting}>
              {t("selectIngredients")}
            </Button>
            ) : null}
            {canEdit ? (
            <Button type="button" onClick={openNew}>
              <Plus className="mr-1.5 h-4 w-4" />
              {t("add")}
            </Button>
            ) : null}
          </div>
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
                  {selecting ? (
                    <GroupSelect
                      ids={group.rows.map((row) => row.id)}
                      selected={selected}
                      onChange={setGroupSelected}
                    />
                  ) : null}
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
                      selecting={selecting}
                      selected={selected.includes(row.id)}
                      onOpen={() => (selecting ? toggleSelected(row.id) : openView(row))}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryState>

      <Card>
        <CardTitle>{t("semiProductCategories")}</CardTitle>
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

      {selected.length > 0 ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--line)] bg-white shadow-lg">
          <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
            <p className="text-sm font-semibold text-[var(--ink)]">{t("selectedCount", { count: selected.length })}</p>
            <div className="min-w-[12rem] flex-1">
              <NativeSelect
                value={assignCategory}
                onChange={(event) => {
                  setAssignCategory(event.target.value);
                  setAssignError(false);
                }}
                className={assignError ? "border-[var(--danger)] bg-red-50" : undefined}
              >
                <option value="">{t("chooseCategory")}</option>
                <option value="none">{t("noCategory")}</option>
                {(categories.list.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </NativeSelect>
            </div>
            {assignError ? (
              <p className="text-sm font-medium text-[var(--danger)]">{t("chooseCategory")}</p>
            ) : null}
            <Button type="button" disabled={semiProducts.assignCategory.isPending} onClick={assignSelected}>
              {t("assignCategory")}
            </Button>
            <ErrorText error={semiProducts.assignCategory.error} />
          </div>
        </div>
      ) : null}

      {mode !== "edit" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <RecipeView
              title={current.name}
              badges={[
                current.category_name ?? "",
                current.is_produced ? t("producedInAdvance") : "",
                current.is_active ? "" : t("inactive"),
              ].filter((badge) => badge !== "")}
              stats={[
                { label: t("yield"), value: `${formatQuantity(current.yield_quantity)} ${units(current.unit)}` },
                { label: t("componentsLabel"), value: String(current.lines.length) },
                ...(current.cost !== undefined
                  ? [
                      {
                        label: t("costPerUnit", { unit: units(current.unit) }),
                        value: formatUnitCost(costPerYieldUnit(current.cost, current.yield_quantity)),
                      },
                    ]
                  : []),
              ]}
              images={current.images}
              compositionTitle={t("composition")}
              lines={current.lines.map((line) => ({ ...line, nested_tech_card: null }))}
              sections={[]}
              method={current.method}
              onEdit={openEdit}
              printHref={null}
              copyPath={null}
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
          title={current === null ? t("newSemiProduct") : draft.name}
          pending={semiProducts.save.isPending}
          error={
            semiProducts.save.error ??
            semiProducts.remove.error ??
            images.upload.error ??
            images.remove.error
          }
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            semiProducts.save.mutate(
              {
                id: current === null ? null : current.id,
                body: {
                  name: draft.name,
                  category: draft.category,
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
                  setIgnoreSemiParam(false);
                  setViewing(saved);
                  setDraft(null);
                  setMode("view");
                  router.replace(`/menu/semi-products?semi=${saved.id}`, { scroll: false });
                },
              },
            )
          }
          onCancel={cancelEdit}
          onDelete={canEdit && current !== null ? () => semiProducts.remove.mutate(current.id, { onSuccess: close }) : null}
          deletePending={semiProducts.remove.isPending}
          headerAction={null}
          below={null}
        >
          <ErrorText error={ingredients.save.error} />
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
          {current !== null ? (
            <MenuImages
              images={(semiProducts.list.data ?? []).find((row) => row.id === current.id)?.images ?? current.images}
              pending={images.upload.isPending || images.remove.isPending}
              onUpload={(file) => images.upload.mutate({ id: current.id, file })}
              onDelete={(imageId) => images.remove.mutate({ id: current.id, imageId })}
            />
          ) : null}
          <CardTitle>{t("composition")}</CardTitle>
          <ComponentLinesEditor
            lines={draft.lines}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={options}
            extraColumn="loss"
            quantityLabel={t("quantity")}
            chooseQuantityUnit={true}
            linePrice={null}
            onCreateSuggestion={null}
            onCreateIngredient={(line, name) => createIngredient(line, name, line.quantity_unit)}
            suggestionPending={ingredients.save.isPending}
          />
        </EditorDialog>
      ) : null}
    </div>
  );
}
