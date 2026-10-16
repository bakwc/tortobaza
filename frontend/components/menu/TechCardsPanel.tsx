"use client";

import { Fragment, useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2, TriangleAlert } from "lucide-react";
import { MarkdownEditor } from "@/components/menu/MarkdownEditor";
import { MenuImages } from "@/components/menu/MenuImages";
import { RecipeView } from "@/components/menu/RecipeView";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  ComponentLinesEditor,
  componentOptions,
  componentValue,
  draftFromLine,
  emptyLine,
  linesToBody,
  newDraftKey,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
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
  formatQuantity,
} from "@/components/menu/ui";
import { useCurrentUser } from "@/hooks/useAuth";
import {
  useIngredients,
  useMissingModifierLines,
  useModifierGroups,
  useSemiProducts,
  useTechCardCategories,
  useTechCardImages,
  useTechCards,
} from "@/hooks/useStock";
import type { ModifierGroup, TechCard } from "@/lib/api/types";

type GroupLinkDraft = { group: number; is_required: boolean | null };

type ModifierComposition = { scales_by_weight: boolean; lines: ComponentLineDraft[] };

type SectionDraft = {
  key: string;
  name: string;
  method: string;
  lines: ComponentLineDraft[];
};

type TechCardDraft = {
  name: string;
  category: number | null;
  kind: "weighted" | "piece";
  basis_weight_kg: string;
  basis_quantity: string;
  method: string;
  is_active: boolean;
  lines: ComponentLineDraft[];
  sections: SectionDraft[];
  groups: GroupLinkDraft[];
  compositions: Record<number, ModifierComposition>;
};

function emptySection(): SectionDraft {
  return { key: newDraftKey(), name: "", method: "", lines: [] };
}

function draftFrom(row: TechCard | null): TechCardDraft {
  if (row === null) {
    return {
      name: "",
      category: null,
      kind: "weighted",
      basis_weight_kg: "1",
      basis_quantity: "1",
      method: "",
      is_active: true,
      lines: [],
      sections: [],
      groups: [],
      compositions: {},
    };
  }
  const compositions: Record<number, ModifierComposition> = {};
  for (const line of row.modifier_lines) {
    const entry = compositions[line.modifier] ?? { scales_by_weight: line.scales_by_weight, lines: [] };
    entry.lines.push(draftFromLine(line));
    compositions[line.modifier] = entry;
  }
  return {
    name: row.name,
    category: row.category,
    kind: row.kind,
    basis_weight_kg: row.basis_weight_kg ?? "",
    basis_quantity: row.basis_quantity === null ? "" : String(row.basis_quantity),
    method: row.method,
    is_active: row.is_active,
    lines: row.lines.map(draftFromLine),
    sections: row.sections.map((section) => ({
      key: newDraftKey(),
      name: section.name,
      method: section.method,
      lines: section.lines.map(draftFromLine),
    })),
    groups: row.modifier_groups.map((link) => ({ group: link.group, is_required: link.is_required })),
    compositions,
  };
}

function withDefaultCompositions(draft: TechCardDraft, groups: ModifierGroup[]): TechCardDraft {
  const compositions = { ...draft.compositions };
  for (const link of draft.groups) {
    for (const modifier of groups.find((group) => group.id === link.group)?.modifiers ?? []) {
      if (!modifier.is_active || compositions[modifier.id]?.lines.length) continue;
      if (modifier.ingredient === null && modifier.semi_product === null) continue;
      compositions[modifier.id] = {
        scales_by_weight: true,
        lines: [{ ...emptyLine(), component: componentValue(modifier) }],
      };
    }
  }
  return { ...draft, compositions };
}

function requiredValue(value: boolean | null): string {
  if (value === null) return "default";
  return value ? "yes" : "no";
}

function parseRequired(value: string): boolean | null {
  if (value === "default") return null;
  return value === "yes";
}

export function TechCardsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const techCards = useTechCards();
  const categories = useTechCardCategories();
  const groups = useModifierGroups();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const missing = useMissingModifierLines();
  const images = useTechCardImages();
  const currentUser = useCurrentUser();
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [viewing, setViewing] = useState<TechCard | null>(null);
  const [draft, setDraft] = useState<TechCardDraft | null>(null);
  const [groupToAdd, setGroupToAdd] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const current =
    viewing === null ? null : (techCards.list.data ?? []).find((row) => row.id === viewing.id) ?? viewing;

  const openView = (row: TechCard) => {
    techCards.save.reset();
    techCards.remove.reset();
    setViewing(row);
    setDraft(null);
    setMode("view");
    setGroupToAdd("");
  };
  const openNew = () => {
    techCards.save.reset();
    techCards.remove.reset();
    setViewing(null);
    setDraft(draftFrom(null));
    setMode("edit");
    setGroupToAdd("");
  };
  const openEdit = () => {
    if (current === null) return;
    setDraft(withDefaultCompositions(draftFrom(current), groups.list.data ?? []));
    setMode("edit");
    setGroupToAdd("");
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
    semiProducts.list.data ?? [],
    "all",
    t("ingredient"),
    t("semiProduct"),
  );
  const allGroups = groups.list.data ?? [];
  const missingByCard = new Map<number, number>();
  for (const row of missing.data ?? []) {
    missingByCard.set(row.tech_card, (missingByCard.get(row.tech_card) ?? 0) + 1);
  }
  const cards = techCards.list.data ?? [];
  const cardGroups = [
    ...(categories.list.data ?? []).map((category) => ({
      key: String(category.id),
      label: category.name,
      cards: cards.filter((row) => row.category === category.id),
    })),
    { key: "none", label: t("noCategory"), cards: cards.filter((row) => row.category === null) },
  ].filter((group) => group.cards.length > 0);
  const columnCount = isFinanceAdmin ? 4 : 3;

  const setComposition = (modifierId: number, patch: Partial<ModifierComposition>) => {
    if (!draft) return;
    const current = draft.compositions[modifierId] ?? { scales_by_weight: true, lines: [] };
    setDraft({ ...draft, compositions: { ...draft.compositions, [modifierId]: { ...current, ...patch } } });
  };

  const submit = () => {
    if (!draft) return;
    const linkedGroupIds = new Set(draft.groups.map((link) => link.group));
    const modifierLines = [];
    for (const group of allGroups) {
      if (!linkedGroupIds.has(group.id)) continue;
      for (const modifier of group.modifiers) {
        const composition = draft.compositions[modifier.id];
        if (!composition) continue;
        for (const line of linesToBody(composition.lines)) {
          modifierLines.push({ ...line, modifier: modifier.id, scales_by_weight: composition.scales_by_weight });
        }
      }
    }
    techCards.save.mutate(
      {
        id: viewing ? viewing.id : null,
        body: {
          name: draft.name,
          category: draft.category,
          kind: draft.kind,
          basis_weight_kg: draft.kind === "weighted" ? draft.basis_weight_kg.replace(",", ".") : null,
          basis_quantity: draft.kind === "piece" ? Number(draft.basis_quantity) : null,
          method: draft.method,
          is_active: draft.is_active,
          lines: linesToBody(draft.lines),
          sections: draft.sections.map((section) => ({
            name: section.name,
            method: section.method,
            lines: linesToBody(section.lines),
          })),
          modifier_groups: draft.groups,
          modifier_lines: modifierLines,
        },
      },
      {
        onSuccess: (saved) => {
          setViewing(saved);
          setDraft(null);
          setMode("view");
        },
      },
    );
  };

  return (
    <div className="grid gap-6">
      {(missing.data ?? []).length > 0 ? (
        <Card className="border-amber-300 bg-amber-50">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
            <TriangleAlert className="h-4 w-4" />
            {t("missingCompositionsTitle")}
          </div>
          <ul className="mt-2 grid gap-1 text-sm text-amber-900">
            {(missing.data ?? []).map((row) => (
              <li key={`${row.tech_card}-${row.modifier}`}>
                {row.tech_card_name}: {row.group_name} — {row.modifier_name}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("menu.techCards")}</CardTitle>
          <Button type="button" size="sm" onClick={openNew}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={techCards.list.isLoading} isError={techCards.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("kind")}</th>
                <th className="py-2">{t("linkedProducts")}</th>
                {isFinanceAdmin ? <th className="py-2 text-right">{t("baseCost")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {cardGroups.map((group) => (
                <Fragment key={group.key}>
                  <tr>
                    <td
                      colSpan={columnCount}
                      className="border-t border-[var(--line)] bg-[var(--cream)] px-2 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/70"
                    >
                      {group.label}
                    </td>
                  </tr>
                  {group.cards.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => openView(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className={row.is_active ? "py-2" : "py-2 text-[var(--muted-2)] line-through"}>
                        <span className="inline-flex items-center gap-1.5">
                          {row.name}
                          {missingByCard.has(row.id) ? (
                            <TriangleAlert className="h-3.5 w-3.5 text-amber-600" aria-label={t("missingCompositionsTitle")} />
                          ) : null}
                        </span>
                      </td>
                      <td className="py-2">
                        {row.kind === "weighted" && row.basis_weight_kg !== null
                          ? t("basisKg", { weight: row.basis_weight_kg })
                          : row.basis_quantity !== null
                            ? t("basisPieces", { count: row.basis_quantity })
                            : t("kindPiece")}
                      </td>
                      <td className="py-2">{row.products.map((product) => product.name).join(", ") || "—"}</td>
                      {isFinanceAdmin ? (
                        <td className="py-2 text-right">
                          {row.base_cost !== undefined ? formatMoney(row.base_cost) : "—"}
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </QueryState>
      </Card>

      <Card>
        <CardTitle>{t("techCardCategories")}</CardTitle>
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

      {mode === "view" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <RecipeView
              title={current.name}
              badges={[
                current.category_name ?? "",
                current.kind === "weighted" && current.basis_weight_kg !== null
                  ? t("basisKg", { weight: current.basis_weight_kg })
                  : current.basis_quantity !== null
                    ? t("basisPieces", { count: current.basis_quantity })
                    : t("kindPiece"),
                current.is_active ? "" : t("inactive"),
                isFinanceAdmin && current.base_cost !== undefined
                  ? current.kind === "weighted"
                    ? `${t("costPerKg", { weight: current.basis_weight_kg ?? "" })}: ${formatMoney(current.base_cost)}`
                    : `${t("costPerPiece", { count: current.basis_quantity ?? 0 })}: ${formatMoney(current.base_cost)}`
                  : "",
              ].filter((badge) => badge !== "")}
              images={current.images}
              compositionTitle={
                current.kind === "weighted"
                  ? t("baseCompositionPerKg", { weight: current.basis_weight_kg ?? "" })
                  : t("baseCompositionPerPiece", { count: current.basis_quantity ?? 0 })
              }
              lines={current.lines}
              sections={current.sections}
              method={current.method}
              onEdit={openEdit}
            >
              {current.products.length > 0 ? (
                <p className="text-sm text-[var(--muted-2)]">
                  {t("linkedProducts")}: {current.products.map((product) => product.name).join(", ")}
                </p>
              ) : null}
              {current.modifier_groups.length > 0 ? (
                <div className="grid gap-3">
                  <CardTitle>{t("modifiers")}</CardTitle>
                  {current.modifier_groups.map((link) => (
                    <div key={link.id} className="grid gap-1">
                      <p className="text-sm font-semibold text-[var(--ink)]">
                        {link.group_name}
                        {link.effective_is_required ? null : (
                          <span className="font-normal text-[var(--muted-2)]"> ({t("optional")})</span>
                        )}
                      </p>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                            <tr>
                              <th className="py-2 pr-3 font-medium">{t("name")}</th>
                              <th className="py-2 pr-3 text-right font-medium">{t("quantity")}</th>
                              <th className="py-2 text-right font-medium">{t("lossPercent")}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {link.modifiers.map((modifier) => {
                              const composition = current.modifier_lines.filter(
                                (line) => line.modifier === modifier.id,
                              );
                              if (composition.length === 0) {
                                return (
                                  <tr key={modifier.id} className="border-t border-[var(--line)]">
                                    <td className="py-2 pr-3">
                                      <span className="inline-flex items-center gap-1.5">
                                        {modifier.name}
                                        <TriangleAlert
                                          className="h-3.5 w-3.5 text-amber-600"
                                          aria-label={t("missingCompositionsTitle")}
                                        />
                                      </span>
                                    </td>
                                    <td className="py-2 pr-3 text-right">—</td>
                                    <td className="py-2 text-right">—</td>
                                  </tr>
                                );
                              }
                              return composition.map((line) => (
                                <tr key={line.id} className="border-t border-[var(--line)]">
                                  <td className="py-2 pr-3">
                                    {line.name === modifier.name ? modifier.name : `${modifier.name}: ${line.name}`}
                                  </td>
                                  <td className="py-2 pr-3 text-right tabular-nums">
                                    {formatQuantity(line.quantity)} {units(line.unit)}
                                  </td>
                                  <td className="py-2 text-right tabular-nums">
                                    {formatQuantity(line.loss_percent)}%
                                  </td>
                                </tr>
                              ));
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </RecipeView>
          </DialogContent>
        </Dialog>
      ) : null}

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : cancelEdit())}
          title={viewing === null ? t("newTechCard") : draft.name}
          pending={techCards.save.isPending}
          error={techCards.save.error ?? techCards.remove.error}
          submitLabel={t("save")}
          onSubmit={submit}
          onCancel={cancelEdit}
          onDelete={viewing === null ? null : () => techCards.remove.mutate(viewing.id, { onSuccess: close })}
          deletePending={techCards.remove.isPending}
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
            <Field label={t("kind")}>
              <NativeSelect
                value={draft.kind}
                onChange={(event) => {
                  const kind = event.target.value as "weighted" | "piece";
                  setDraft({
                    ...draft,
                    kind,
                    basis_weight_kg: kind === "weighted" && draft.basis_weight_kg === "" ? "1" : draft.basis_weight_kg,
                    basis_quantity: kind === "piece" && draft.basis_quantity === "" ? "1" : draft.basis_quantity,
                  });
                }}
              >
                <option value="weighted">{t("kindWeighted")}</option>
                <option value="piece">{t("kindPiece")}</option>
              </NativeSelect>
            </Field>
            {draft.kind === "weighted" ? (
              <Field label={t("basisWeight")} className="sm:col-span-3">
                <Input
                  required
                  inputMode="decimal"
                  value={draft.basis_weight_kg}
                  onChange={(event) => setDraft({ ...draft, basis_weight_kg: event.target.value })}
                />
              </Field>
            ) : (
              <Field label={t("basisQuantity")} className="sm:col-span-3">
                <Input
                  required
                  inputMode="numeric"
                  value={draft.basis_quantity}
                  onChange={(event) => setDraft({ ...draft, basis_quantity: event.target.value })}
                />
              </Field>
            )}
            <div className="flex items-end pb-3">
              <CheckboxField
                label={t("isActive")}
                checked={draft.is_active}
                onChange={(value) => setDraft({ ...draft, is_active: value })}
              />
            </div>
          </div>

          {viewing && viewing.products.length > 0 ? (
            <p className="text-sm text-[var(--muted-2)]">
              {t("linkedProducts")}: {viewing.products.map((product) => product.name).join(", ")}
            </p>
          ) : null}
          {viewing && isFinanceAdmin && viewing.base_cost !== undefined ? (
            <p className="text-sm text-[var(--ink)]">
              {draft.kind === "weighted"
                ? t("costPerKg", { weight: draft.basis_weight_kg })
                : t("costPerPiece", { count: draft.basis_quantity })}
              : {formatMoney(viewing.base_cost)}
            </p>
          ) : null}

          <Field label={t("method")}>
            <MarkdownEditor value={draft.method} onChange={(method) => setDraft({ ...draft, method })} />
          </Field>

          {viewing ? (
            <MenuImages
              images={(techCards.list.data ?? []).find((row) => row.id === viewing.id)?.images ?? viewing.images}
              pending={images.upload.isPending || images.remove.isPending}
              onUpload={(file) => images.upload.mutate({ id: viewing.id, file })}
              onDelete={(imageId) => images.remove.mutate({ id: viewing.id, imageId })}
            />
          ) : null}

          <CardTitle>
            {draft.kind === "weighted"
              ? t("baseCompositionPerKg", { weight: draft.basis_weight_kg })
              : t("baseCompositionPerPiece", { count: draft.basis_quantity })}
          </CardTitle>
          <ComponentLinesEditor
            lines={draft.lines}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={options}
            extraColumn="loss"
            quantityLabel={t("quantity")}
          />

          <CardTitle>{t("sections")}</CardTitle>
          {draft.sections.map((section) => (
            <div key={section.key} className="grid gap-3 rounded-2xl border border-[var(--line)] p-4">
              <div className="flex items-center gap-2">
                <Input
                  required
                  value={section.name}
                  placeholder={t("sectionName")}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      sections: draft.sections.map((row) =>
                        row.key === section.key ? { ...row, name: event.target.value } : row,
                      ),
                    })
                  }
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("removeLine")}
                  onClick={() =>
                    setDraft({ ...draft, sections: draft.sections.filter((row) => row.key !== section.key) })
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <ComponentLinesEditor
                lines={section.lines}
                onChange={(lines) =>
                  setDraft({
                    ...draft,
                    sections: draft.sections.map((row) => (row.key === section.key ? { ...row, lines } : row)),
                  })
                }
                options={options}
                extraColumn="loss"
                quantityLabel={t("quantity")}
              />
              <Field label={t("method")}>
                <MarkdownEditor
                  value={section.method}
                  onChange={(method) =>
                    setDraft({
                      ...draft,
                      sections: draft.sections.map((row) => (row.key === section.key ? { ...row, method } : row)),
                    })
                  }
                />
              </Field>
            </div>
          ))}
          <div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDraft({ ...draft, sections: [...draft.sections, emptySection()] })}
            >
              <Plus className="mr-1 h-4 w-4" />
              {t("addSection")}
            </Button>
          </div>

          <CardTitle>{t("modifiers")}</CardTitle>
          {draft.groups.map((link) => {
            const group = allGroups.find((row) => row.id === link.group);
            if (!group) return null;
            return (
              <div key={link.group} className="grid gap-3 rounded-2xl border border-[var(--line)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-[var(--ink)]">{group.name}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <NativeSelect
                      value={requiredValue(link.is_required)}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          groups: draft.groups.map((row) =>
                            row.group === link.group
                              ? { ...row, is_required: parseRequired(event.target.value) }
                              : row,
                          ),
                        })
                      }
                    >
                      <option value="default">
                        {t("requiredDefault", { value: group.is_required ? t("yes") : t("no") })}
                      </option>
                      <option value="yes">{t("required")}</option>
                      <option value="no">{t("optional")}</option>
                    </NativeSelect>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setDraft({ ...draft, groups: draft.groups.filter((row) => row.group !== link.group) })
                      }
                    >
                      <Trash2 className="mr-1 h-4 w-4" />
                      {t("delete")}
                    </Button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                      <tr>
                        <th className="py-2 pr-3 font-medium">{t("name")}</th>
                        <th className="py-2 pr-3 text-right font-medium">{t("quantity")}</th>
                        <th className="py-2 text-right font-medium">{t("lossPercent")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.modifiers
                        .filter((modifier) => modifier.is_active)
                        .map((modifier) => {
                          const composition = draft.compositions[modifier.id] ?? {
                            scales_by_weight: true,
                            lines: [],
                          };
                          const line = composition.lines[0];
                          const unit = options.find((option) => option.value === line?.component)?.unit;
                          return (
                            <tr key={modifier.id} className="border-t border-[var(--line)]">
                              <td className="py-2 pr-3">
                                <span className="inline-flex items-center gap-1.5">
                                  {modifier.name}
                                  {line ? null : (
                                    <TriangleAlert
                                      className="h-3.5 w-3.5 text-amber-600"
                                      aria-label={t("missingCompositionsTitle")}
                                    />
                                  )}
                                </span>
                              </td>
                              <td className="py-2 pr-3">
                                {line ? (
                                  <div className="relative ml-auto w-36">
                                    <Input
                                      required
                                      inputMode="decimal"
                                      value={line.quantity}
                                      onChange={(event) =>
                                        setComposition(modifier.id, {
                                          lines: [{ ...line, quantity: event.target.value }],
                                        })
                                      }
                                      className="pr-12 text-right"
                                    />
                                    <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                                      {unit ? units(unit) : ""}
                                    </span>
                                  </div>
                                ) : (
                                  <p className="text-right">—</p>
                                )}
                              </td>
                              <td className="py-2">
                                {line ? (
                                  <div className="relative ml-auto w-28">
                                    <Input
                                      inputMode="decimal"
                                      value={line.loss_percent}
                                      onChange={(event) =>
                                        setComposition(modifier.id, {
                                          lines: [{ ...line, loss_percent: event.target.value }],
                                        })
                                      }
                                      className="pr-8 text-right"
                                    />
                                    <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                                      %
                                    </span>
                                  </div>
                                ) : (
                                  <p className="text-right">—</p>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
          <div className="flex flex-wrap gap-2">
            <NativeSelect value={groupToAdd} onChange={(event) => setGroupToAdd(event.target.value)}>
              <option value="">{t("chooseGroup")}</option>
              {allGroups
                .filter((group) => !draft.groups.some((link) => link.group === group.id))
                .map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
            </NativeSelect>
            <Button
              type="button"
              variant="outline"
              disabled={groupToAdd === ""}
              onClick={() => {
                setDraft(
                  withDefaultCompositions(
                    { ...draft, groups: [...draft.groups, { group: Number(groupToAdd), is_required: null }] },
                    allGroups,
                  ),
                );
                setGroupToAdd("");
              }}
            >
              <Plus className="mr-1 h-4 w-4" />
              {t("addGroup")}
            </Button>
          </div>
          {allGroups.every((group) => draft.groups.some((link) => link.group === group.id)) ? (
            <p className="text-xs text-[var(--muted-2)]">{t("noGroupsToAdd")}</p>
          ) : null}
        </EditorDialog>
      ) : null}
    </div>
  );
}
