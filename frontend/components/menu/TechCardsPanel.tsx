"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  BookOpen,
  Check,
  ChefHat,
  ChevronRight,
  Hash,
  Layers,
  Package,
  Plus,
  Scale,
  Search,
  SlidersHorizontal,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { MarkdownEditor } from "@/components/menu/MarkdownEditor";
import { MenuImages } from "@/components/menu/MenuImages";
import { RecipeHeading, RecipeTable, RecipeView, type RecipeTableRow } from "@/components/menu/RecipeView";
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
import { useRouter } from "@/i18n/navigation";
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
import { cn } from "@/lib/utils";

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

function componentsTotal(row: TechCard): number {
  return row.lines.length + row.sections.reduce((sum, section) => sum + section.lines.length, 0);
}

function TechCardRow({
  row,
  basis,
  missing,
  isFinanceAdmin,
  onOpen,
}: {
  row: TechCard;
  basis: string;
  missing: number;
  isFinanceAdmin: boolean;
  onOpen: () => void;
}) {
  const t = useTranslations("stock");
  const cover = row.images[0];
  const KindIcon = row.kind === "weighted" ? Scale : Hash;
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
          <KindIcon className="h-5 w-5" />
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
          {missing > 0 ? (
            <span
              title={t("missingCompositionsTitle")}
              className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900"
            >
              <TriangleAlert className="h-3 w-3" />
              {missing}
            </span>
          ) : null}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[var(--muted-2)]">
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" />
            {t("componentsCount", { count: componentsTotal(row) })}
          </span>
          {row.sections.length > 0 ? (
            <span className="flex items-center gap-1">
              <BookOpen className="h-3.5 w-3.5" />
              {t("sectionsCount", { count: row.sections.length })}
            </span>
          ) : null}
          {row.modifier_groups.length > 0 ? (
            <span className="flex items-center gap-1">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {t("groupsCount", { count: row.modifier_groups.length })}
            </span>
          ) : null}
        </div>
      </div>
      <span className="hidden shrink-0 items-center gap-1 rounded-full bg-[var(--cream)] px-2.5 py-1 text-xs font-semibold text-[var(--ink)] sm:flex">
        <KindIcon className="h-3.5 w-3.5 text-[var(--brand)]" />
        {basis}
      </span>
      {isFinanceAdmin && row.base_cost !== undefined ? (
        <span className="w-24 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
          {formatMoney(row.base_cost)}
        </span>
      ) : null}
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </button>
  );
}

export function TechCardsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const router = useRouter();
  const searchParams = useSearchParams();
  const techCards = useTechCards();
  const categories = useTechCardCategories();
  const groups = useModifierGroups();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const missing = useMissingModifierLines();
  const images = useTechCardImages();
  const currentUser = useCurrentUser();
  const isFinanceAdmin = Boolean(currentUser.data?.is_finance_admin);
  const cardParam = searchParams.get("card");
  const paramId = cardParam === null ? null : Number(cardParam);
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [viewing, setViewing] = useState<TechCard | null>(null);
  const [ignoreCardParam, setIgnoreCardParam] = useState(false);
  const [draft, setDraft] = useState<TechCardDraft | null>(null);
  const [groupToAdd, setGroupToAdd] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const requestedId = ignoreCardParam
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
      : ((techCards.list.data ?? []).find((row) => row.id === requestedId) ??
        (viewing !== null && viewing.id === requestedId ? viewing : null));

  useEffect(() => {
    if (ignoreCardParam && cardParam === null) setIgnoreCardParam(false);
  }, [ignoreCardParam, cardParam]);

  const openView = (row: TechCard) => {
    techCards.save.reset();
    techCards.remove.reset();
    setIgnoreCardParam(false);
    setViewing(row);
    setDraft(null);
    setMode("view");
    setGroupToAdd("");
    router.replace(`/menu?card=${row.id}`, { scroll: false });
  };
  const openNew = () => {
    techCards.save.reset();
    techCards.remove.reset();
    setIgnoreCardParam(true);
    setViewing(null);
    setDraft(draftFrom(null));
    setMode("edit");
    setGroupToAdd("");
    router.replace("/menu", { scroll: false });
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
    setIgnoreCardParam(true);
    setViewing(null);
    router.replace("/menu", { scroll: false });
  };
  const cancelEdit = () => {
    setDraft(null);
    if (current === null) close();
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
  const query = search.trim().toLowerCase();
  const allCardGroups = [
    ...(categories.list.data ?? []).map((category) => ({
      key: String(category.id),
      label: category.name,
      cards: cards.filter((row) => row.category === category.id),
    })),
    { key: "none", label: t("noCategory"), cards: cards.filter((row) => row.category === null) },
  ].filter((group) => group.cards.length > 0);
  const cardGroups = allCardGroups
    .filter((group) => categoryFilter === "all" || group.key === categoryFilter)
    .map((group) => ({ ...group, cards: group.cards.filter((row) => row.name.toLowerCase().includes(query)) }))
    .filter((group) => group.cards.length > 0);
  const activeCount = cards.filter((row) => row.is_active).length;
  const basisLabel = (row: TechCard) =>
    row.kind === "weighted" && row.basis_weight_kg !== null
      ? t("basisKg", { weight: row.basis_weight_kg })
      : row.basis_quantity !== null
        ? t("basisPieces", { count: row.basis_quantity })
        : t("kindPiece");

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
        id: current ? current.id : null,
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
          setIgnoreCardParam(false);
          setViewing(saved);
          setDraft(null);
          setMode("view");
          router.replace(`/menu?card=${saved.id}`, { scroll: false });
        },
      },
    );
  };

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--ink)]">{t("menu.techCards")}</h2>
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
          {[{ key: "all", label: t("allCategories"), count: cards.length }, ...allCardGroups.map((group) => ({
            key: group.key,
            label: group.label,
            count: group.cards.length,
          }))].map((chip) => (
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
            <span className="font-bold">{cards.length}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <Check className="h-4 w-4" />
            <span>{t("activeCount")}</span>
            <span className="font-bold">
              {activeCount} / {cards.length}
            </span>
          </div>
          {missingByCard.size > 0 ? (
            <div className="flex items-center gap-1.5 text-amber-700">
              <TriangleAlert className="h-4 w-4" />
              <span>{t("missingCompositionsTitle")}</span>
              <span className="font-bold">{missingByCard.size}</span>
            </div>
          ) : null}
        </div>
      </Card>

      <QueryState isLoading={techCards.list.isLoading} isError={techCards.list.isError}>
        {cardGroups.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-3xl border border-[var(--line)] bg-white p-12 text-center">
            <ChefHat className="h-12 w-12 text-[var(--muted)]" />
            <p className="mt-4 text-base font-semibold text-[var(--ink)]">{t("nothingFound")}</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {cardGroups.map((group) => (
              <section
                key={group.key}
                className="overflow-hidden rounded-3xl border border-[var(--line)] bg-white shadow-sm"
              >
                <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
                  <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">
                    {group.label}
                  </h3>
                  <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
                    {group.cards.length}
                  </span>
                </div>
                <div className="divide-y divide-[var(--line)]">
                  {group.cards.map((row) => (
                    <TechCardRow
                      key={row.id}
                      row={row}
                      basis={basisLabel(row)}
                      missing={missingByCard.get(row.id) ?? 0}
                      isFinanceAdmin={isFinanceAdmin}
                      onOpen={() => openView(row)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryState>

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

      {mode !== "edit" && current ? (
        <Dialog open onOpenChange={(value) => (value ? null : close())}>
          <DialogContent className="w-[min(900px,calc(100vw-1.5rem))] overflow-y-auto p-6">
            <DialogDescription className="hidden">{current.name}</DialogDescription>
            <RecipeView
              title={current.name}
              badges={[current.category_name ?? "", current.is_active ? "" : t("inactive")].filter(
                (badge) => badge !== "",
              )}
              stats={[
                {
                  label: t("kind"),
                  value: `${current.kind === "weighted" ? t("kindWeighted") : t("kindPiece")} · ${basisLabel(current)}`,
                },
                { label: t("componentsLabel"), value: String(componentsTotal(current)) },
                ...(isFinanceAdmin && current.base_cost !== undefined
                  ? [
                      {
                        label:
                          current.kind === "weighted"
                            ? t("costPerKg", { weight: current.basis_weight_kg ?? "" })
                            : t("costPerPiece", { count: current.basis_quantity ?? 0 }),
                        value: formatMoney(current.base_cost),
                      },
                    ]
                  : []),
              ]}
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
              printHref={`/menu/${current.id}/print`}
              copyPath={`/menu?card=${current.id}`}
            >
              {current.products.length > 0 ? (
                <p className="text-sm text-[var(--muted-2)]">
                  {t("linkedProducts")}:{" "}
                  <span className="text-[var(--ink)]">
                    {current.products.map((product) => product.name).join(", ")}
                  </span>
                </p>
              ) : null}
              {current.modifier_groups.length > 0 ? (
                <div className="grid gap-4">
                  <RecipeHeading number={null} title={t("modifiers")} note="" />
                  {current.modifier_groups.map((link) => (
                    <div key={link.id} className="grid gap-1">
                      <p className="text-sm font-semibold text-[var(--ink)]">
                        {link.group_name}
                        <span className="font-normal text-[var(--muted-2)]">
                          {" · "}
                          {link.selection_type === "single" ? t("selectionSingle") : t("selectionMulti")}
                          {" · "}
                          {link.effective_is_required ? t("required") : t("optional")}
                        </span>
                      </p>
                      <RecipeTable
                        rows={link.modifiers.flatMap((modifier): RecipeTableRow[] => {
                          const composition = current.modifier_lines.filter(
                            (line) => line.modifier === modifier.id,
                          );
                          if (composition.length === 0) {
                            return [
                              {
                                key: `m${modifier.id}`,
                                name: modifier.name,
                                tag: null,
                                amount: "—",
                                loss: "—",
                                warning: true,
                              },
                            ];
                          }
                          return composition.map((line) => {
                            const loss = formatQuantity(line.loss_percent);
                            return {
                              key: String(line.id),
                              name: line.name === modifier.name ? modifier.name : `${modifier.name}: ${line.name}`,
                              tag: null,
                              amount: `${formatQuantity(line.quantity)} ${units(line.unit)}`,
                              loss: loss === "0" ? "—" : `${loss}%`,
                              warning: false,
                            };
                          });
                        })}
                      />
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
          title={current === null ? t("newTechCard") : draft.name}
          pending={techCards.save.isPending}
          error={techCards.save.error ?? techCards.remove.error}
          submitLabel={t("save")}
          onSubmit={submit}
          onCancel={cancelEdit}
          onDelete={current === null ? null : () => techCards.remove.mutate(current.id, { onSuccess: close })}
          deletePending={techCards.remove.isPending}
          below={null}
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

          {current && current.products.length > 0 ? (
            <p className="text-sm text-[var(--muted-2)]">
              {t("linkedProducts")}: {current.products.map((product) => product.name).join(", ")}
            </p>
          ) : null}
          {current && isFinanceAdmin && current.base_cost !== undefined ? (
            <p className="text-sm text-[var(--ink)]">
              {draft.kind === "weighted"
                ? t("costPerKg", { weight: draft.basis_weight_kg })
                : t("costPerPiece", { count: draft.basis_quantity })}
              : {formatMoney(current.base_cost)}
            </p>
          ) : null}

          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{t("method")}</span>
            <MarkdownEditor value={draft.method} onChange={(method) => setDraft({ ...draft, method })} />
          </div>

          {current ? (
            <MenuImages
              images={(techCards.list.data ?? []).find((row) => row.id === current.id)?.images ?? current.images}
              pending={images.upload.isPending || images.remove.isPending}
              onUpload={(file) => images.upload.mutate({ id: current.id, file })}
              onDelete={(imageId) => images.remove.mutate({ id: current.id, imageId })}
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
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{t("method")}</span>
                <MarkdownEditor
                  value={section.method}
                  onChange={(method) =>
                    setDraft({
                      ...draft,
                      sections: draft.sections.map((row) => (row.key === section.key ? { ...row, method } : row)),
                    })
                  }
                />
              </div>
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
