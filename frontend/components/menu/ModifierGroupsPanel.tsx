"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  componentOptions,
  componentRef,
  componentValue,
  newDraftKey,
  techCardOptions,
} from "@/components/menu/ComponentLinesEditor";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { Card, CardTitle, CheckboxField, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import {
  useCatalogOptions,
  useIngredients,
  useModifierGroups,
  useSemiProducts,
  useTechCardCategories,
  useTechCards,
} from "@/hooks/useStock";
import type { Modifier, ModifierGroup } from "@/lib/api/types";

type ModifierDraft = {
  key: string;
  id: number | null;
  name: string;
  catalog_option: number | null;
  component: string;
  is_active: boolean;
};

function modifierComponent(modifier: Modifier): string {
  if (modifier.ingredient === null && modifier.semi_product === null && modifier.nested_tech_card === null) {
    return "";
  }
  return componentValue(modifier);
}

type GroupDraft = {
  name: string;
  selection_type: "single" | "multi";
  is_required: boolean;
  is_global: boolean;
  categories: number[];
  min_selections: string;
  max_selections: string;
  position: number;
  modifiers: ModifierDraft[];
};

function draftFrom(row: ModifierGroup | null, position: number): GroupDraft {
  if (row === null) {
    return {
      name: "",
      selection_type: "single",
      is_required: false,
      is_global: false,
      categories: [],
      min_selections: "0",
      max_selections: "",
      position,
      modifiers: [],
    };
  }
  return {
    name: row.name,
    selection_type: row.selection_type,
    is_required: row.is_required,
    is_global: row.is_global,
    categories: row.categories,
    min_selections: String(row.min_selections),
    max_selections: row.max_selections === null ? "" : String(row.max_selections),
    position: row.position,
    modifiers: row.modifiers.map((modifier) => ({
      key: newDraftKey(),
      id: modifier.id,
      name: modifier.name,
      catalog_option: modifier.catalog_option,
      component: modifierComponent(modifier),
      is_active: modifier.is_active,
    })),
  };
}

export function ModifierGroupsPanel() {
  const t = useTranslations("stock");
  const tForms = useTranslations("forms");
  const canEdit = useCan("edit_menu");
  const groups = useModifierGroups();
  const categories = useTechCardCategories();
  const catalogOptions = useCatalogOptions();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const techCards = useTechCards();
  const components = [
    ...componentOptions(
      ingredients.list.data ?? [],
      semiProducts.list.data ?? [],
      "all",
      t("ingredient"),
      t("semiProduct"),
    ),
    ...techCardOptions(techCards.list.data ?? [], t("techCard")),
  ];
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<GroupDraft | null>(null);

  const open = (row: ModifierGroup | null) => {
    groups.save.reset();
    groups.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(draftFrom(row, (groups.list.data ?? []).length));
  };
  const close = () => setDraft(null);

  const updateModifier = (key: string, patch: Partial<ModifierDraft>) => {
    if (!draft) return;
    setDraft({
      ...draft,
      modifiers: draft.modifiers.map((row) => (row.key === key ? { ...row, ...patch } : row)),
    });
  };

  const usedOptions = new Set(
    (draft?.modifiers ?? []).map((row) => row.catalog_option).filter((value) => value !== null),
  );
  const ownIds = new Set((draft?.modifiers ?? []).map((row) => row.id).filter((value) => value !== null));

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("menu.modifierGroups")}</CardTitle>
          {canEdit ? (
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
          ) : null}
        </div>
        <p className="mt-2 text-xs text-[var(--muted-2)]">{t("modifierGroupsHint")}</p>
        <QueryState isLoading={groups.list.isLoading} isError={groups.list.isError}>
          <div className="mt-4 grid gap-3">
            {(groups.list.data ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-[var(--ink)]">{row.name}</span>
                  <span className="text-xs text-[var(--muted-2)]">
                    {row.selection_type === "single" ? t("selectionSingle") : t("selectionMulti")}
                    {row.is_required ? ` · ${t("required")}` : ""}
                    {row.is_global ? ` · ${t("global")}` : ""}
                    {!row.is_global && row.categories.length > 0
                      ? ` · ${(categories.list.data ?? [])
                          .filter((category) => row.categories.includes(category.id))
                          .map((category) => category.name)
                          .join(", ")}`
                      : ""}
                  </span>
                </div>
                <p className="mt-1 text-sm text-[var(--muted-2)]">
                  {row.modifiers.map((modifier) => modifier.name).join(", ") || "—"}
                </p>
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
          title={editingId === null ? t("newModifierGroup") : draft.name}
          pending={groups.save.isPending}
          error={groups.save.error ?? groups.remove.error}
          submitLabel={canEdit ? t("save") : null}
          onSubmit={() =>
            groups.save.mutate(
              {
                id: editingId,
                body: {
                  name: draft.name,
                  selection_type: draft.selection_type,
                  is_required: draft.is_required,
                  is_global: draft.is_global,
                  categories: draft.is_global ? [] : draft.categories,
                  min_selections: Number(draft.min_selections || "0"),
                  max_selections: draft.max_selections === "" ? null : Number(draft.max_selections),
                  position: draft.position,
                  modifiers: draft.modifiers.map((row) => ({
                    id: row.id,
                    name: row.name,
                    catalog_option: row.catalog_option,
                    ...(row.component === ""
                      ? { ingredient: null, semi_product: null, nested_tech_card: null }
                      : componentRef(row.component)),
                    is_active: row.is_active,
                  })),
                },
              },
              { onSuccess: close },
            )
          }
          onDelete={canEdit && editingId !== null ? () => groups.remove.mutate(editingId, { onSuccess: close }) : null}
          deletePending={groups.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-4 sm:grid-cols-4">
            <Field label={t("name")} className="sm:col-span-4">
              <Input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            </Field>
            <Field label={t("selectionType")}>
              <NativeSelect
                value={draft.selection_type}
                onChange={(event) =>
                  setDraft({ ...draft, selection_type: event.target.value as "single" | "multi" })
                }
              >
                <option value="single">{t("selectionSingle")}</option>
                <option value="multi">{t("selectionMulti")}</option>
              </NativeSelect>
            </Field>
            {draft.selection_type === "multi" ? (
              <>
                <Field label={t("minSelections")}>
                  <Input
                    name="min_selections"
                    required
                    inputMode="numeric"
                    value={draft.min_selections}
                    onChange={(event) => setDraft({ ...draft, min_selections: event.target.value })}
                  />
                </Field>
                <Field label={t("maxSelections")}>
                  <Input
                    inputMode="numeric"
                    value={draft.max_selections}
                    onChange={(event) => setDraft({ ...draft, max_selections: event.target.value })}
                  />
                </Field>
              </>
            ) : (
              <span className="hidden sm:col-span-2 sm:block" />
            )}
            <div className="flex items-end gap-4 pb-3">
              <CheckboxField
                label={t("required")}
                checked={draft.is_required}
                onChange={(value) => setDraft({ ...draft, is_required: value })}
              />
              <CheckboxField
                label={t("global")}
                checked={draft.is_global}
                onChange={(value) =>
                  setDraft({ ...draft, is_global: value, categories: value ? [] : draft.categories })
                }
              />
            </div>
            {!draft.is_global ? (
              <Field label={t("techCardCategories")} className="sm:col-span-4">
                <div className="flex flex-wrap gap-4">
                  {(categories.list.data ?? []).map((category) => (
                    <CheckboxField
                      key={category.id}
                      label={category.name}
                      checked={draft.categories.includes(category.id)}
                      onChange={(value) =>
                        setDraft({
                          ...draft,
                          categories: value
                            ? [...draft.categories, category.id]
                            : draft.categories.filter((id) => id !== category.id),
                        })
                      }
                    />
                  ))}
                </div>
              </Field>
            ) : null}
          </div>
          <CardTitle>{t("modifiers")}</CardTitle>
          <div className="grid gap-2">
            {draft.modifiers.map((row, index) => (
              <div
                key={row.key}
                data-field-group={tForms("rowNumber", { number: index + 1 })}
                data-error-list="modifiers"
                className="grid grid-cols-[1fr_auto] gap-2 sm:grid-cols-[1fr_1fr_1fr_auto_auto]"
              >
                <Input
                  name="name"
                  required
                  placeholder={t("name")}
                  value={row.name}
                  onChange={(event) => updateModifier(row.key, { name: event.target.value })}
                  className="col-span-2 sm:col-span-1"
                />
                <NativeSelect
                  value={row.catalog_option ?? ""}
                  onChange={(event) =>
                    updateModifier(row.key, {
                      catalog_option: event.target.value === "" ? null : Number(event.target.value),
                    })
                  }
                >
                  <option value="">{t("noWebsiteOption")}</option>
                  {(catalogOptions.data ?? []).map((option) => {
                    const takenElsewhere =
                      option.modifier !== null && !ownIds.has(option.modifier);
                    const takenHere = usedOptions.has(option.id) && row.catalog_option !== option.id;
                    return (
                      <option key={option.id} value={option.id} disabled={takenElsewhere || takenHere}>
                        {option.label}
                      </option>
                    );
                  })}
                </NativeSelect>
                <SearchSelect
                  options={[{ value: "", label: t("noDefaultComponent") }, ...components]}
                  value={row.component}
                  onChange={(component) => updateModifier(row.key, { component })}
                  placeholder={t("noDefaultComponent")}
                  required={false}
                  name={null}
                  className=""
                  onCreate={null}
                  createPending={false}
                />
                <div className="flex items-center">
                  <CheckboxField
                    label={t("isActive")}
                    checked={row.is_active}
                    onChange={(value) => updateModifier(row.key, { is_active: value })}
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("removeLine")}
                  onClick={() =>
                    setDraft({ ...draft, modifiers: draft.modifiers.filter((item) => item.key !== row.key) })
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  setDraft({
                    ...draft,
                    modifiers: [
                      ...draft.modifiers,
                      {
                        key: newDraftKey(),
                        id: null,
                        name: "",
                        catalog_option: null,
                        component: "",
                        is_active: true,
                      },
                    ],
                  })
                }
              >
                <Plus className="mr-1 h-4 w-4" />
                {t("addModifier")}
              </Button>
            </div>
          </div>
          <p className="text-xs text-[var(--muted-2)]">{t("websiteOptionHint")}</p>
          <p className="text-xs text-[var(--muted-2)]">{t("defaultComponentHint")}</p>
        </EditorDialog>
      ) : null}
    </div>
  );
}
