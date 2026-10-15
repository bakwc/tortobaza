"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  ErrorText,
  Field,
  NativeSelect,
  QueryState,
  formatMoney,
} from "@/components/menu/ui";
import { useCurrentUser } from "@/hooks/useAuth";
import {
  useIngredients,
  useMissingModifierLines,
  useModifierGroups,
  useSemiProducts,
  useTechCardCategories,
  useTechCards,
} from "@/hooks/useStock";
import type { TechCard } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type GroupLinkDraft = { group: number; is_required: boolean | null };

type ModifierComposition = { scales_by_weight: boolean; lines: ComponentLineDraft[] };

type TechCardDraft = {
  name: string;
  category: number | null;
  kind: "weighted" | "piece";
  is_active: boolean;
  lines: ComponentLineDraft[];
  groups: GroupLinkDraft[];
  compositions: Record<number, ModifierComposition>;
};

function draftFrom(row: TechCard | null): TechCardDraft {
  if (row === null) {
    return {
      name: "",
      category: null,
      kind: "weighted",
      is_active: true,
      lines: [],
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
    is_active: row.is_active,
    lines: row.lines.map(draftFromLine),
    groups: row.modifier_groups.map((link) => ({ group: link.group, is_required: link.is_required })),
    compositions,
  };
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
  const techCards = useTechCards();
  const categories = useTechCardCategories();
  const groups = useModifierGroups();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const missing = useMissingModifierLines();
  const currentUser = useCurrentUser();
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);
  const [editing, setEditing] = useState<TechCard | null>(null);
  const [draft, setDraft] = useState<TechCardDraft | null>(null);
  const [groupToAdd, setGroupToAdd] = useState("");
  const [newCategory, setNewCategory] = useState("");

  const open = (row: TechCard | null) => {
    techCards.save.reset();
    techCards.remove.reset();
    setEditing(row);
    setDraft(draftFrom(row));
    setGroupToAdd("");
  };
  const close = () => setDraft(null);

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
        id: editing ? editing.id : null,
        body: {
          name: draft.name,
          category: draft.category,
          kind: draft.kind,
          is_active: draft.is_active,
          lines: linesToBody(draft.lines),
          modifier_groups: draft.groups,
          modifier_lines: modifierLines,
        },
      },
      { onSuccess: close },
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
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={techCards.list.isLoading} isError={techCards.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("category")}</th>
                <th className="py-2">{t("kind")}</th>
                <th className="py-2">{t("linkedProducts")}</th>
                {isFinanceAdmin ? <th className="py-2 text-right">{t("baseCost")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {(techCards.list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
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
                  <td className="py-2">{row.category_name ?? "—"}</td>
                  <td className="py-2">{row.kind === "weighted" ? t("kindWeighted") : t("kindPiece")}</td>
                  <td className="py-2">{row.products.map((product) => product.name).join(", ") || "—"}</td>
                  {isFinanceAdmin ? (
                    <td className="py-2 text-right">
                      {row.base_cost !== undefined ? formatMoney(row.base_cost) : "—"}
                    </td>
                  ) : null}
                </tr>
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

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          title={editing === null ? t("newTechCard") : draft.name}
          pending={techCards.save.isPending}
          error={techCards.save.error ?? techCards.remove.error}
          submitLabel={t("save")}
          onSubmit={submit}
          onDelete={editing === null ? null : () => techCards.remove.mutate(editing.id, { onSuccess: close })}
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
                onChange={(event) => setDraft({ ...draft, kind: event.target.value as "weighted" | "piece" })}
              >
                <option value="weighted">{t("kindWeighted")}</option>
                <option value="piece">{t("kindPiece")}</option>
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

          {editing && editing.products.length > 0 ? (
            <p className="text-sm text-[var(--muted-2)]">
              {t("linkedProducts")}: {editing.products.map((product) => product.name).join(", ")}
            </p>
          ) : null}
          {editing && isFinanceAdmin && editing.base_cost !== undefined ? (
            <p className="text-sm text-[var(--ink)]">
              {draft.kind === "weighted" ? t("costPerKg") : t("costPerPiece")}: {formatMoney(editing.base_cost)}
            </p>
          ) : null}

          <CardTitle>{draft.kind === "weighted" ? t("baseCompositionPerKg") : t("baseCompositionPerPiece")}</CardTitle>
          <ComponentLinesEditor
            lines={draft.lines}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={options}
            extraColumn="loss"
            quantityLabel={t("quantity")}
          />

          <CardTitle>{t("linkedGroups")}</CardTitle>
          <div className="grid gap-2">
            {draft.groups.map((link) => {
              const group = allGroups.find((row) => row.id === link.group);
              return (
                <div key={link.group} className="grid grid-cols-[1fr_12rem_auto] items-center gap-2">
                  <span className="text-sm font-medium text-[var(--ink)]">{group?.name ?? link.group}</span>
                  <NativeSelect
                    value={requiredValue(link.is_required)}
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        groups: draft.groups.map((row) =>
                          row.group === link.group ? { ...row, is_required: parseRequired(event.target.value) } : row,
                        ),
                      })
                    }
                  >
                    <option value="default">
                      {t("requiredDefault", { value: group?.is_required ? t("yes") : t("no") })}
                    </option>
                    <option value="yes">{t("required")}</option>
                    <option value="no">{t("optional")}</option>
                  </NativeSelect>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={t("removeLine")}
                    onClick={() =>
                      setDraft({ ...draft, groups: draft.groups.filter((row) => row.group !== link.group) })
                    }
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              );
            })}
            <div className="flex gap-2">
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
                  setDraft({ ...draft, groups: [...draft.groups, { group: Number(groupToAdd), is_required: null }] });
                  setGroupToAdd("");
                }}
              >
                {t("add")}
              </Button>
            </div>
          </div>

          {draft.groups.length > 0 ? <CardTitle>{t("modifierCompositions")}</CardTitle> : null}
          {draft.groups.map((link) => {
            const group = allGroups.find((row) => row.id === link.group);
            if (!group) return null;
            return (
              <div key={link.group} className="grid gap-3 rounded-2xl border border-[var(--line)] p-4">
                <p className="text-sm font-semibold text-[var(--ink)]">{group.name}</p>
                {group.modifiers
                  .filter((modifier) => modifier.is_active)
                  .map((modifier) => {
                    const composition = draft.compositions[modifier.id] ?? { scales_by_weight: true, lines: [] };
                    const empty = composition.lines.length === 0;
                    return (
                      <div
                        key={modifier.id}
                        className={cn(
                          "grid gap-2 rounded-xl p-3",
                          empty ? "bg-amber-50 ring-1 ring-amber-300" : "bg-[var(--cream)]/40",
                        )}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="inline-flex items-center gap-1.5 text-sm font-medium">
                            {modifier.name}
                            {empty ? <TriangleAlert className="h-3.5 w-3.5 text-amber-600" /> : null}
                          </span>
                          {draft.kind === "weighted" ? (
                            <CheckboxField
                              label={t("scalesByWeight")}
                              checked={composition.scales_by_weight}
                              onChange={(value) => setComposition(modifier.id, { scales_by_weight: value })}
                            />
                          ) : null}
                        </div>
                        <ComponentLinesEditor
                          lines={composition.lines}
                          onChange={(lines) => setComposition(modifier.id, { lines })}
                          options={options}
                          extraColumn="loss"
                          quantityLabel={t("quantity")}
                        />
                      </div>
                    );
                  })}
              </div>
            );
          })}
        </EditorDialog>
      ) : null}
    </div>
  );
}
