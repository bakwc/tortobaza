"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
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
  Upload,
} from "lucide-react";
import { MarkdownEditor } from "@/components/menu/MarkdownEditor";
import { MenuImages } from "@/components/menu/MenuImages";
import {
  componentHref,
  RecipeHeading,
  RecipeTable,
  RecipeView,
  type RecipeTableRow,
} from "@/components/menu/RecipeView";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  ComponentLinesEditor,
  QuantityUnitControl,
  componentOptions,
  componentValue,
  defaultQuantityUnit,
  draftFromLine,
  draftLoss,
  emptyLine,
  isSectionComponent,
  linesToBody,
  newDraftKey,
  techCardOptions,
  type ComponentLineDraft,
  type ComponentOption,
} from "@/components/menu/ComponentLinesEditor";
import { formatShelfLife, shelfLifeDraft, shelfLifeSeconds } from "@/components/menu/shelfLife";
import { CloneNameDialog } from "@/components/menu/CloneNameDialog";
import { EditorDialog } from "@/components/menu/EditorDialog";
import {
  Card,
  CardTitle,
  CheckboxField,
  ErrorText,
  Field,
  GroupSelect,
  NativeSelect,
  QueryState,
  formatLineAmount,
  formatLossLabel,
  formatMoney,
  lossPercentText,
} from "@/components/menu/ui";
import { useCan } from "@/hooks/useAuth";
import { getPathname, useRouter } from "@/i18n/navigation";
import {
  useIngredients,
  useMissingModifierLines,
  useModifierGroups,
  useSemiProducts,
  useTechCard,
  useTechCardCategories,
  useTechCardDrafts,
  useTechCardImages,
  useTechCardImport,
  useTechCardList,
} from "@/hooks/useStock";
import type { IngredientBody, MenuUnit, ModifierGroup, TechCard, TechCardDraftRecord, TechCardImport, TechCardImportLine, TechCardListItem } from "@/lib/api/types";
import { compareNameMatch, nameMatches } from "@/lib/nameMatch";
import {
  deleteStoredTechCardDraft,
  findStoredTechCardDraftByCard,
  flushPendingTechCardDrafts,
  listStoredTechCardDrafts,
  mergeServerTechCardDrafts,
  pushStoredTechCardDraft,
  readStoredTechCardDraft,
  techCardDraftsEqual,
  writeStoredTechCardDraft,
  type ModifierComposition,
  type SectionDraft,
  type StoredTechCardDraft,
  type TechCardDraft,
} from "@/lib/tech-card-draft";
import { cn } from "@/lib/utils";

function formatCostRange(
  min: string,
  max: string,
  range: (values: { min: string; max: string }) => string,
): string {
  if (min === max) return formatMoney(min);
  return range({ min: formatMoney(min), max: formatMoney(max) });
}

function perPieceCost(value: string, count: number): string {
  return String(Number(value) / count);
}

function displayedCost(value: string, kind: TechCard["kind"], basisQuantity: number | null): string {
  if (kind === "weighted") return value;
  return perPieceCost(value, basisQuantity as number);
}

function savedLines(lines: ComponentLineDraft[]) {
  return linesToBody(lines).map((line) => ({
    ...line,
    quantity: line.quantity.trim() === "" ? null : line.quantity,
  }));
}

function sectionGrams(section: SectionDraft): string {
  let total = 0;
  for (const line of section.lines) {
    if (line.quantity_unit !== "g") continue;
    const value = Number(line.quantity.replace(",", "."));
    if (!Number.isFinite(value)) continue;
    total += value;
  }
  return String(Math.round(total * 1000) / 1000);
}

function baseLines(draft: TechCardDraft): ComponentLineDraft[] {
  return draft.lines.map((line) => {
    if (!isSectionComponent(line.component)) return line;
    const key = line.component.slice("section:".length);
    const section = draft.sections.find((row) => row.key === key);
    return {
      ...line,
      quantity: section === undefined ? "0" : sectionGrams(section),
      quantity_unit: "g",
      loss_quantity: "",
    };
  });
}

function savedBaseLines(draft: TechCardDraft) {
  return baseLines(draft).map((line) => {
    const key = isSectionComponent(line.component) ? line.component.slice("section:".length) : null;
    const section = key === null ? undefined : draft.sections.find((row) => row.key === key);
    const body = savedLines([line])[0];
    return {
      ...body,
      nested_section_name: section === undefined ? null : section.name.trim(),
      quantity: section === undefined ? body.quantity : null,
      quantity_unit: section === undefined ? body.quantity_unit : "g",
      loss_quantity: section === undefined ? body.loss_quantity : "0",
    };
  });
}

function sectionOptions(sections: SectionDraft[], label: string): ComponentOption[] {
  return sections
    .filter((section) => section.name.trim() !== "")
    .map((section) => ({
      value: `section:${section.key}`,
      label: `${label}: ${section.name.trim()}`,
      unit: "g",
      ingredient: false,
      grams_per_unit: null,
    }));
}

function emptySection(): SectionDraft {
  return { key: newDraftKey(), id: null, name: "", method: "", lines: [] };
}

function importLine(line: TechCardImportLine): ComponentLineDraft {
  const component =
    line.ingredient_id !== null
      ? `ingredient:${line.ingredient_id}`
      : line.semi_product_id !== null
        ? `semi_product:${line.semi_product_id}`
        : "";
  return {
    key: newDraftKey(),
    component,
    quantity: line.quantity,
    quantity_unit: line.unit,
    loss_quantity: draftLoss(line.loss_quantity),
    unit_cost: "",
    suggestion:
      component === ""
        ? { name: line.name, unit: line.unit, kind: line.suggested_kind, original_text: line.original_text }
        : null,
  };
}

function draftFromImport(row: TechCardImport): TechCardDraft {
  return {
    name: row.name,
    category: null,
    kind: row.kind,
    basis_weight_kg: row.basis_weight_kg ?? "1",
    basis_quantity: row.basis_quantity === null ? "1" : String(row.basis_quantity),
    sale_price: "",
    method: row.method,
    shelf_life_days: "",
    shelf_life_hours: "",
    storage_temperature: "",
    is_active: true,
    lines: row.lines.map(importLine),
    sections: row.sections.map((section) => ({
      key: newDraftKey(),
      id: null,
      name: section.name,
      method: section.method,
      lines: section.lines.map(importLine),
    })),
    groups: [],
    compositions: {},
  };
}

function patchDraftLine(draft: TechCardDraft, key: string, patch: Partial<ComponentLineDraft>): TechCardDraft {
  const apply = (line: ComponentLineDraft) => (line.key === key ? { ...line, ...patch } : line);
  return {
    ...draft,
    lines: draft.lines.map(apply),
    sections: draft.sections.map((section) => ({ ...section, lines: section.lines.map(apply) })),
  };
}

function draftFrom(row: TechCard | null): TechCardDraft {
  if (row === null) {
    return {
      name: "",
      category: null,
      kind: "weighted",
      basis_weight_kg: "1",
      basis_quantity: "1",
      sale_price: "",
      method: "",
      shelf_life_days: "",
      shelf_life_hours: "",
      storage_temperature: "",
      is_active: true,
      lines: [],
      sections: [],
      groups: [],
      compositions: {},
    };
  }
  const stored = shelfLifeDraft(row.shelf_life_seconds);
  const compositions: Record<number, ModifierComposition> = {};
  for (const line of row.modifier_lines) {
    if (line.is_global) continue;
    const entry = compositions[line.modifier] ?? { scales_by_weight: line.scales_by_weight, lines: [] };
    entry.lines.push(draftFromLine(line));
    compositions[line.modifier] = entry;
  }
  const sections = row.sections.map((section) => ({
    key: newDraftKey(),
    id: section.id,
    name: section.name,
    method: section.method,
    lines: section.lines.map(draftFromLine),
  }));
  const sectionKey = new Map(sections.map((section) => [section.id, section.key]));
  return {
    name: row.name,
    category: row.category,
    kind: row.kind,
    basis_weight_kg: row.basis_weight_kg ?? "",
    basis_quantity: row.basis_quantity === null ? "" : String(row.basis_quantity),
    sale_price: row.sale_price ?? "",
    method: row.method,
    shelf_life_days: stored.days,
    shelf_life_hours: stored.hours,
    storage_temperature: row.storage_temperature ?? "",
    is_active: row.is_active,
    lines: row.lines.map((line) => {
      const draft = draftFromLine(line);
      if (line.nested_section !== null) {
        const key = sectionKey.get(line.nested_section);
        draft.component = key === undefined ? "" : `section:${key}`;
        draft.quantity_unit = "g";
        draft.loss_quantity = "";
      }
      return draft;
    }),
    sections,
    groups: row.modifier_groups
      .filter((link) => !link.is_global)
      .map((link) => ({ group: link.group, is_required: link.is_required })),
    compositions,
  };
}

function withDefaultCompositions(
  draft: TechCardDraft,
  groups: ModifierGroup[],
  options: ComponentOption[],
): TechCardDraft {
  const compositions = { ...draft.compositions };
  for (const link of draft.groups) {
    for (const modifier of groups.find((group) => group.id === link.group)?.modifiers ?? []) {
      if (!modifier.is_active || compositions[modifier.id]?.lines.length) continue;
      if (modifier.ingredient === null && modifier.semi_product === null && modifier.nested_tech_card === null) {
        continue;
      }
      const option = options.find((row) => row.value === componentValue(modifier));
      if (option === undefined) continue;
      compositions[modifier.id] = {
        scales_by_weight: true,
        lines: [{ ...emptyLine(), component: option.value, quantity_unit: defaultQuantityUnit(option) }],
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

function techCardDraftRows(records: TechCardDraftRecord[]) {
  const rows = new Map<
    string,
    {
      clientId: string;
      techCardId: number | null;
      name: string;
      updatedBy: string;
      pending: boolean;
      clientUpdatedAt: string;
      draft: TechCardDraft;
    }
  >();
  for (const record of records) {
    const key = record.tech_card !== null ? `card:${record.tech_card}` : record.client_id;
    rows.set(key, {
      clientId: record.client_id,
      techCardId: record.tech_card,
      name: record.name,
      updatedBy: record.updated_by,
      pending: false,
      clientUpdatedAt: record.client_updated_at,
      draft: record.payload as TechCardDraft,
    });
  }
  for (const local of listStoredTechCardDrafts()) {
    const key = local.techCardId !== null ? `card:${local.techCardId}` : local.clientId;
    const existing = rows.get(key);
    if (
      existing !== undefined &&
      !local.pending &&
      Date.parse(local.clientUpdatedAt) < Date.parse(existing.clientUpdatedAt)
    ) {
      continue;
    }
    rows.set(key, {
      clientId: local.clientId,
      techCardId: local.techCardId,
      name: local.draft.name,
      updatedBy: existing?.updatedBy ?? "",
      pending: local.pending,
      clientUpdatedAt: local.clientUpdatedAt,
      draft: local.draft,
    });
  }
  return [...rows.values()];
}

function TechCardRow({
  row,
  basis,
  missing,
  selecting,
  selected,
  onOpen,
}: {
  row: TechCardListItem;
  basis: string;
  missing: number;
  selecting: boolean;
  selected: boolean;
  onOpen: () => void;
}) {
  const t = useTranslations("stock");
  const cover = row.images[0];
  const KindIcon = row.kind === "weighted" ? Scale : Hash;
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
            {t("componentsCount", { count: row.components_count })}
          </span>
          {row.sections_count > 0 ? (
            <span className="flex items-center gap-1">
              <BookOpen className="h-3.5 w-3.5" />
              {t("sectionsCount", { count: row.sections_count })}
            </span>
          ) : null}
          {row.groups_count > 0 ? (
            <span className="flex items-center gap-1">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {t("groupsCount", { count: row.groups_count })}
            </span>
          ) : null}
        </div>
      </div>
      <span className="hidden w-28 shrink-0 items-center justify-center gap-1 rounded-full bg-[var(--cream)] px-2.5 py-1 text-xs font-semibold text-[var(--ink)] sm:flex">
        <KindIcon className="h-3.5 w-3.5 text-[var(--brand)]" />
        {basis}
      </span>
      <span className="w-28 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--ink)]">
        {row.sale_price !== null ? (
          <>
            {formatMoney(row.sale_price)}
            <span className="block text-[11px] font-normal text-[var(--muted-2)]">
              {t("salePricePerPiece", { count: 1 })}
            </span>
          </>
        ) : (
          "—"
        )}
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--brand)]" />
    </button>
  );
}

export function TechCardsPanel() {
  const t = useTranslations("stock");
  const tForms = useTranslations("forms");
  const units = useTranslations("stock.units");
  const locale = useLocale();
  const router = useRouter();
  const searchParams = useSearchParams();
  const techCards = useTechCardList();
  const categories = useTechCardCategories();
  const groups = useModifierGroups();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const missing = useMissingModifierLines();
  const images = useTechCardImages();
  const techCardImport = useTechCardImport();
  const fileRef = useRef<HTMLInputElement>(null);
  const baselineRef = useRef<TechCardDraft | null>(null);
  const clientIdRef = useRef<string | null>(null);
  const techCardIdRef = useRef<number | null>(null);
  const pendingApplyRef = useRef<StoredTechCardDraft | null>(null);
  const persistTimer = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const draftsQuery = useTechCardDrafts();
  const canSeeCosts = useCan("view_costs");
  const canEdit = useCan("edit_menu");
  const cardParam = searchParams.get("card");
  const paramId = cardParam === null ? null : Number(cardParam);
  const [mode, setMode] = useState<"view" | "edit" | null>(null);
  const [openedId, setOpenedId] = useState<number | null>(null);
  const [ignoreCardParam, setIgnoreCardParam] = useState(false);
  const [draft, setDraft] = useState<TechCardDraft | null>(null);
  const [groupToAdd, setGroupToAdd] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [assignCategory, setAssignCategory] = useState("");
  const [importedFrom, setImportedFrom] = useState<string | null>(null);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [draftRevision, setDraftRevision] = useState(0);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [restoreDraft, setRestoreDraft] = useState<TechCardDraft | null>(null);
  const requestedId = ignoreCardParam
    ? openedId
    : openedId !== null
      ? openedId
      : paramId !== null && Number.isFinite(paramId)
        ? paramId
        : null;
  const card = useTechCard(requestedId);
  const current = card.data ?? null;

  useEffect(() => {
    if (ignoreCardParam && cardParam === null) setIgnoreCardParam(false);
  }, [ignoreCardParam, cardParam]);

  const rememberDrafts = () => {
    setDraftRevision((value) => value + 1);
  };
  const refreshServerDrafts = () => {
    void queryClient.invalidateQueries({ queryKey: ["menu", "tech-card-drafts"] });
  };
  const syncStored = (row: StoredTechCardDraft) => {
    void pushStoredTechCardDraft(row, clientIdRef.current === row.clientId).then((result) => {
      rememberDrafts();
      if (result === "saved") refreshServerDrafts();
    });
  };

  useEffect(() => {
    if (draftsQuery.data === undefined) return;
    mergeServerTechCardDrafts(
      draftsQuery.data,
      clientIdRef.current,
      mode === "edit" ? techCardIdRef.current : null,
    );
    rememberDrafts();
  }, [draftsQuery.data, mode]);

  useEffect(() => {
    const flush = () => {
      void flushPendingTechCardDrafts(clientIdRef.current).then(() => {
        rememberDrafts();
        refreshServerDrafts();
      });
    };
    flush();
    window.addEventListener("online", flush);
    return () => window.removeEventListener("online", flush);
  }, [queryClient]);

  useEffect(() => {
    if (mode !== "edit" || draft === null || baselineRef.current === null || restoreOpen) return;
    const clientId = clientIdRef.current;
    const techCardId = techCardIdRef.current;
    const baseline = baselineRef.current;
    if (clientId === null) return;
    persistTimer.current = window.setTimeout(() => {
      persistTimer.current = null;
      if (techCardDraftsEqual(draft, baseline)) {
        if (readStoredTechCardDraft(clientId) !== null) {
          void deleteStoredTechCardDraft(clientId).then(() => {
            rememberDrafts();
            refreshServerDrafts();
          });
        }
        return;
      }
      const row: StoredTechCardDraft = {
        clientId,
        techCardId,
        clientUpdatedAt: new Date().toISOString(),
        pending: true,
        rejectedAt: null,
        draft,
      };
      writeStoredTechCardDraft(row);
      rememberDrafts();
      syncStored(row);
    }, 500);
    return () => {
      if (persistTimer.current !== null) {
        window.clearTimeout(persistTimer.current);
        persistTimer.current = null;
      }
    };
  }, [draft, mode, restoreOpen, queryClient]);

  useEffect(() => {
    if (mode !== "edit" || draft === null || baselineRef.current === null) return;
    if (techCardDraftsEqual(draft, baselineRef.current)) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [draft, mode]);

  const openView = (row: TechCardListItem) => {
    techCards.save.reset();
    techCards.remove.reset();
    setIgnoreCardParam(false);
    setOpenedId(row.id);
    setDraft(null);
    setMode("view");
    setGroupToAdd("");
    setImportedFrom(null);
    router.replace(`/menu?card=${row.id}`, { scroll: false });
  };
  const stopPersist = () => {
    if (persistTimer.current !== null) {
      window.clearTimeout(persistTimer.current);
      persistTimer.current = null;
    }
  };
  const persistNow = (next: TechCardDraft) => {
    stopPersist();
    const baseline = baselineRef.current;
    const clientId = clientIdRef.current;
    if (baseline === null || clientId === null) return;
    if (techCardDraftsEqual(next, baseline)) {
      if (readStoredTechCardDraft(clientId) !== null) {
        void deleteStoredTechCardDraft(clientId).then(() => {
          rememberDrafts();
          refreshServerDrafts();
        });
      }
      return;
    }
    const existing = readStoredTechCardDraft(clientId);
    if (existing !== null && techCardDraftsEqual(existing.draft, next)) return;
    const row: StoredTechCardDraft = {
      clientId,
      techCardId: techCardIdRef.current,
      clientUpdatedAt: new Date().toISOString(),
      pending: true,
      rejectedAt: null,
      draft: next,
    };
    writeStoredTechCardDraft(row);
    rememberDrafts();
    syncStored(row);
  };
  const beginEdit = (baseline: TechCardDraft, techCardId: number | null, clientId: string, editor: TechCardDraft) => {
    stopPersist();
    baselineRef.current = baseline;
    techCardIdRef.current = techCardId;
    clientIdRef.current = clientId;
    pendingApplyRef.current = null;
    setRestoreDraft(null);
    setRestoreOpen(false);
    setDraft(editor);
    setMode("edit");
  };
  const openNew = () => {
    techCards.save.reset();
    techCards.remove.reset();
    setIgnoreCardParam(true);
    setOpenedId(null);
    setGroupToAdd("");
    setImportedFrom(null);
    router.replace("/menu", { scroll: false });
    const baseline = draftFrom(null);
    beginEdit(baseline, null, crypto.randomUUID(), baseline);
  };
  const openEdit = () => {
    if (current === null) return;
    setGroupToAdd("");
    setImportedFrom(null);
    const baseline = withDefaultCompositions(draftFrom(current), groups.list.data ?? [], options);
    const stored = findStoredTechCardDraftByCard(current.id);
    const clientId = stored === null ? crypto.randomUUID() : stored.clientId;
    beginEdit(baseline, current.id, clientId, baseline);
    if (stored !== null && !techCardDraftsEqual(stored.draft, baseline)) {
      setRestoreDraft(stored.draft);
      setRestoreOpen(true);
    }
  };
  const openClone = () => {
    techCards.clone.reset();
    setCloneOpen(true);
  };
  const close = () => {
    setRestoreOpen(false);
    setRestoreDraft(null);
    baselineRef.current = null;
    clientIdRef.current = null;
    techCardIdRef.current = null;
    pendingApplyRef.current = null;
    setMode(null);
    setDraft(null);
    setIgnoreCardParam(true);
    setOpenedId(null);
    setImportedFrom(null);
    router.replace("/menu", { scroll: false });
  };
  const cancelEdit = () => {
    setRestoreOpen(false);
    setRestoreDraft(null);
    setDraft(null);
    baselineRef.current = null;
    clientIdRef.current = null;
    techCardIdRef.current = null;
    pendingApplyRef.current = null;
    if (current === null) close();
    else setMode("view");
  };
  const requestClose = () => {
    if (restoreOpen) return;
    if (draft !== null) persistNow(draft);
    cancelEdit();
  };
  const forgetDraft = (clientId: string) => {
    const local = readStoredTechCardDraft(clientId);
    const techCardId = local === null ? null : local.techCardId;
    const ids = new Set<string>([clientId]);
    if (techCardId !== null) {
      for (const record of draftsQuery.data ?? []) {
        if (record.tech_card === techCardId) ids.add(record.client_id);
      }
      const stored = findStoredTechCardDraftByCard(techCardId);
      if (stored !== null) ids.add(stored.clientId);
    }
    for (const id of ids) {
      void deleteStoredTechCardDraft(id).then(() => {
        rememberDrafts();
        refreshServerDrafts();
      });
    }
  };
  const resetDraft = (clientId: string) => {
    stopPersist();
    const editing = clientIdRef.current === clientId;
    forgetDraft(clientId);
    if (editing) cancelEdit();
  };
  const keepStoredDraft = () => {
    if (restoreDraft !== null) setDraft(restoreDraft);
    setImportedFrom(null);
    setRestoreOpen(false);
  };
  const dropStoredDraft = () => {
    const clientId = clientIdRef.current;
    if (clientId !== null) forgetDraft(clientId);
    setRestoreDraft(null);
    setRestoreOpen(false);
  };
  const openStoredDraft = (row: StoredTechCardDraft) => {
    techCards.save.reset();
    techCards.remove.reset();
    setGroupToAdd("");
    setImportedFrom(null);
    if (row.techCardId === null) {
      beginEdit(draftFrom(null), null, row.clientId, row.draft);
      setIgnoreCardParam(true);
      setOpenedId(null);
      router.replace("/menu", { scroll: false });
      return;
    }
    stopPersist();
    baselineRef.current = null;
    clientIdRef.current = row.clientId;
    techCardIdRef.current = row.techCardId;
    pendingApplyRef.current = row;
    setRestoreDraft(null);
    setRestoreOpen(false);
    setIgnoreCardParam(false);
    setOpenedId(row.techCardId);
    setDraft(row.draft);
    setMode("edit");
    router.replace(`/menu?card=${row.techCardId}`, { scroll: false });
  };
  const openImported = (file: File) => {
    techCardImport.mutate(file, {
      onSuccess: (result) => {
        techCards.save.reset();
        techCards.remove.reset();
        setIgnoreCardParam(true);
        setOpenedId(null);
        setImportedFrom(result.source_name);
        setGroupToAdd("");
        router.replace("/menu", { scroll: false });
        beginEdit(draftFrom(null), null, crypto.randomUUID(), draftFromImport(result));
      },
    });
  };
  const selectIngredient = (lineKey: string, id: number) => {
    setDraft((currentDraft) =>
      currentDraft === null
        ? currentDraft
        : patchDraftLine(currentDraft, lineKey, { component: `ingredient:${id}`, suggestion: null }),
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
  const createSuggestion = (line: ComponentLineDraft, kind: "ingredient" | "semi_product") => {
    if (line.suggestion === null) return;
    const suggestion = line.suggestion;
    if (kind === "ingredient") {
      createIngredient(line, suggestion.name, suggestion.unit);
      return;
    }
    semiProducts.save.mutate(
      {
        id: null,
        body: {
          name: suggestion.name,
          category: null,
          unit: suggestion.unit,
          yield_quantity: line.quantity.replace(",", "."),
          is_produced: false,
          is_active: true,
          method: "",
          lines: [],
        },
      },
      {
        onSuccess: (created) =>
          setDraft((currentDraft) =>
            currentDraft === null
              ? currentDraft
              : patchDraftLine(currentDraft, line.key, {
                  component: `semi_product:${created.id}`,
                  suggestion: null,
                }),
          ),
      },
    );
  };
  const toggleSelecting = () => {
    setSelecting((value) => !value);
    setSelected([]);
    setAssignCategory("");
    techCards.assignCategory.reset();
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
    techCards.assignCategory.mutate(
      { ids: selected, category: assignCategory === "none" ? null : Number(assignCategory) },
      { onSuccess: () => setSelected([]) },
    );
  };
  const printSelected = () => {
    const path = getPathname({ locale, href: `/menu/print?ids=${selected.join(",")}` });
    window.open(path, "_blank", "noreferrer");
  };

  const options = [
    ...componentOptions(
      ingredients.list.data ?? [],
      semiProducts.list.data ?? [],
      "all",
      t("ingredient"),
      t("semiProduct"),
    ),
    ...techCardOptions(techCards.list.data ?? [], t("techCard")),
  ];
  const allGroups = groups.list.data ?? [];
  const missingByCard = new Map<number, number>();
  for (const row of missing.data ?? []) {
    missingByCard.set(row.tech_card, (missingByCard.get(row.tech_card) ?? 0) + 1);
  }
  const cards = techCards.list.data ?? [];
  const query = search.trim().toLowerCase();
  const draftRows = useMemo(() => {
    return techCardDraftRows(draftsQuery.data ?? []).filter((row) => nameMatches(row.name, query));
  }, [draftsQuery.data, draftRevision, query]);

  useEffect(() => {
    const pending = pendingApplyRef.current;
    if (pending === null || pending.techCardId === null || current === null || current.id !== pending.techCardId) {
      return;
    }
    baselineRef.current = withDefaultCompositions(draftFrom(current), groups.list.data ?? [], options);
    pendingApplyRef.current = null;
  }, [current, groups.list.data, options]);
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
    .map((group) => ({
      ...group,
      cards: group.cards
        .filter((row) => nameMatches(row.name, query))
        .sort((left, right) => compareNameMatch(left.name, right.name, query)),
    }))
    .filter((group) => group.cards.length > 0);
  const activeCount = cards.filter((row) => row.is_active).length;
  const basisLabel = (row: Pick<TechCardListItem, "kind" | "basis_weight_kg" | "basis_quantity">) =>
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
        for (const line of savedLines(composition.lines)) {
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
          sale_price: draft.sale_price.trim() === "" ? null : draft.sale_price.replace(",", "."),
          method: draft.method,
          shelf_life_seconds: shelfLifeSeconds(draft.shelf_life_days, draft.shelf_life_hours),
          storage_temperature: draft.storage_temperature.trim() === "" ? null : draft.storage_temperature.trim(),
          is_active: draft.is_active,
          lines: savedBaseLines(draft),
          sections: draft.sections.map((section) => ({
            name: section.name,
            method: section.method,
            lines: savedLines(section.lines),
          })),
          modifier_groups: draft.groups,
          modifier_lines: modifierLines,
        },
      },
      {
        onSuccess: (saved) => {
          stopPersist();
          const clientId = clientIdRef.current;
          clientIdRef.current = null;
          techCardIdRef.current = null;
          pendingApplyRef.current = null;
          if (clientId !== null) {
            void deleteStoredTechCardDraft(clientId).then(() => {
              rememberDrafts();
              refreshServerDrafts();
            });
          }
          setIgnoreCardParam(false);
          setOpenedId(saved.id);
          setRestoreOpen(false);
          setRestoreDraft(null);
          setDraft(null);
          baselineRef.current = null;
          setMode("view");
          router.replace(`/menu?card=${saved.id}`, { scroll: false });
        },
      },
    );
  };

  return (
    <div className={cn("grid gap-6", selected.length > 0 && "pb-28")}>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--ink)]">{t("menu.techCards")}</h2>
          <div className="flex flex-wrap items-center gap-2">
            {canEdit ? (
            <Button type="button" variant={selecting ? "primary" : "outline"} onClick={toggleSelecting}>
              {t("selectIngredients")}
            </Button>
            ) : null}
            {canEdit ? (
            <Button
              type="button"
              variant="outline"
              disabled={techCardImport.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {techCardImport.isPending ? <Spinner className="mr-1.5 h-4 w-4" /> : <Upload className="mr-1.5 h-4 w-4" />}
              {techCardImport.isPending ? t("menu.recognizingTechCard") : t("menu.importTechCard")}
            </Button>
            ) : null}
            {canEdit ? (
            <Button type="button" onClick={openNew}>
              <Plus className="mr-1.5 h-4 w-4" />
              {t("add")}
            </Button>
            ) : null}
            <input
              ref={fileRef}
              type="file"
              accept=".docx,.pages,.pdf"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file !== undefined) openImported(file);
              }}
            />
          </div>
        </div>
        <ErrorText error={techCardImport.error} />
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

      {draftRows.length > 0 ? (
        <section className="overflow-hidden rounded-3xl border border-[var(--line)] bg-white shadow-sm">
          <div className="flex items-center gap-2.5 border-b border-[var(--line)] bg-[var(--cream-soft)] px-4 py-3">
            <h3 className="flex-1 text-sm font-semibold uppercase tracking-wide text-[var(--ink)]/70">{t("drafts")}</h3>
            <span className="rounded-full bg-[var(--cream)] px-2.5 py-0.5 text-xs font-semibold text-[var(--ink)]/70">
              {draftRows.length}
            </span>
          </div>
          <div className="divide-y divide-[var(--line)]">
            {draftRows.map((row) => (
              <div key={row.clientId} className="flex items-center gap-2 px-4 py-3">
                <button
                  type="button"
                  onClick={() =>
                    openStoredDraft({
                      clientId: row.clientId,
                      techCardId: row.techCardId,
                      clientUpdatedAt: row.clientUpdatedAt,
                      pending: row.pending,
                      rejectedAt: null,
                      draft: row.draft,
                    })
                  }
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="font-semibold text-[var(--ink)]">{row.name.trim() === "" ? t("newTechCard") : row.name}</p>
                  {[row.updatedBy, row.pending ? t("draftNotSent") : ""].filter((part) => part !== "").length > 0 ? (
                    <p className="mt-0.5 text-xs text-[var(--muted-2)]">
                      {[row.updatedBy, row.pending ? t("draftNotSent") : ""].filter((part) => part !== "").join(" · ")}
                    </p>
                  ) : null}
                </button>
                {canEdit ? (
                  <Button type="button" variant="outline" onClick={() => resetDraft(row.clientId)}>
                    {t("resetDraft")}
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

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
                  {selecting ? (
                    <GroupSelect
                      ids={group.cards.map((row) => row.id)}
                      selected={selected}
                      onChange={setGroupSelected}
                    />
                  ) : null}
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
            <Button type="button" variant="outline" onClick={printSelected}>
              {t("print")}
            </Button>
            <Button type="button" disabled={techCards.assignCategory.isPending} onClick={assignSelected}>
              {t("assignCategory")}
            </Button>
            <ErrorText error={techCards.assignCategory.error} />
          </div>
        </div>
      ) : null}

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
                ...(current.sale_price !== null
                  ? [
                      {
                        label: t("salePricePerPiece", { count: 1 }),
                        value: formatMoney(current.sale_price),
                      },
                    ]
                  : []),
                ...(current.shelf_life_seconds !== null
                  ? [
                      {
                        label: t("shelfLife"),
                        value: formatShelfLife(
                          current.shelf_life_seconds,
                          (count) => t("shelfLifeDays", { count }),
                          (count) => t("shelfLifeHours", { count }),
                        ),
                      },
                    ]
                  : []),
                ...(current.storage_temperature !== null
                  ? [
                      {
                        label: t("storageTemperature"),
                        value: current.storage_temperature,
                      },
                    ]
                  : []),
                ...(canSeeCosts && current.cost_min !== undefined && current.cost_max !== undefined
                  ? [
                      {
                        label:
                          current.kind === "weighted"
                            ? t("costPerKg", { weight: current.basis_weight_kg ?? "" })
                            : t("costPerPiece", { count: 1 }),
                        value: formatCostRange(
                          displayedCost(current.cost_min, current.kind, current.basis_quantity),
                          displayedCost(current.cost_max, current.kind, current.basis_quantity),
                          (values) => t("costRange", values),
                        ),
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
              onClone={canEdit ? openClone : null}
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
              {current.modifier_groups.some((link) => !link.is_global) ? (
                <div className="grid gap-4">
                  <RecipeHeading number={null} title={t("modifiers")} note="" />
                  {current.modifier_groups.filter((link) => !link.is_global).map((link) => (
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
                                href: null,
                                tag: null,
                                amount: "—",
                                loss: "",
                                cost: null,
                                warning: true,
                              },
                            ];
                          }
                          return composition.map((line) => {
                            return {
                              key: String(line.id),
                              name: line.name === modifier.name ? modifier.name : `${modifier.name}: ${line.name}`,
                              href:
                                line.nested_tech_card !== null
                                  ? `/menu?card=${line.nested_tech_card}`
                                  : componentHref(line.ingredient, line.semi_product),
                              tag: null,
                              amount: formatLineAmount(line.quantity, units(line.quantity_unit)),
                              loss: formatLossLabel(line.quantity, line.loss_quantity, units(line.quantity_unit)),
                              cost: line.cost === undefined ? null : formatMoney(line.cost),
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

      {cloneOpen && current !== null ? (
        <CloneNameDialog
          name={current.name}
          pending={techCards.clone.isPending}
          error={techCards.clone.error}
          onOpenChange={(value) => (value ? null : setCloneOpen(false))}
          onSubmit={(name) =>
            techCards.clone.mutate(
              { id: current.id, name },
              {
                onSuccess: (saved) => {
                  setCloneOpen(false);
                  setIgnoreCardParam(false);
                  setOpenedId(saved.id);
                  setDraft(null);
                  setMode("view");
                  router.replace(`/menu?card=${saved.id}`, { scroll: false });
                },
              },
            )
          }
        />
      ) : null}

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : requestClose())}
          title={current === null ? t("newTechCard") : draft.name}
          pending={techCards.save.isPending}
          error={
            techCards.save.error ??
            techCards.remove.error ??
            images.upload.error ??
            images.remove.error
          }
          submitLabel={canEdit ? t("save") : null}
          onSubmit={submit}
          onCancel={requestClose}
          onDelete={
            canEdit && current !== null
              ? () =>
                  techCards.remove.mutate(current.id, {
                    onSuccess: () => {
                      stopPersist();
                      const stored = findStoredTechCardDraftByCard(current.id);
                      if (stored !== null) {
                        void deleteStoredTechCardDraft(stored.clientId).then(() => {
                          rememberDrafts();
                          refreshServerDrafts();
                        });
                      }
                      close();
                    },
                  })
              : null
          }
          deletePending={techCards.remove.isPending}
          headerAction={
            canEdit && clientIdRef.current !== null ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  const clientId = clientIdRef.current;
                  if (clientId !== null) resetDraft(clientId);
                }}
              >
                {t("resetDraft")}
              </Button>
            ) : null
          }
          below={null}
        >
          {importedFrom !== null && current === null ? (
            <p className="text-sm text-[var(--muted-2)]">{t("menu.importedFrom", { name: importedFrom })}</p>
          ) : null}
          <ErrorText error={ingredients.save.error ?? semiProducts.save.error} />
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
            <Field label={t("salePricePerPiece", { count: 1 })} className="sm:col-span-3">
              <Input
                inputMode="decimal"
                value={draft.sale_price}
                onChange={(event) => setDraft({ ...draft, sale_price: event.target.value })}
              />
            </Field>
            <Field label={t("shelfLifeDaysLabel")}>
              <Input
                inputMode="numeric"
                value={draft.shelf_life_days}
                onChange={(event) => setDraft({ ...draft, shelf_life_days: event.target.value })}
              />
            </Field>
            <Field label={t("shelfLifeHoursLabel")}>
              <Input
                inputMode="numeric"
                value={draft.shelf_life_hours}
                onChange={(event) => setDraft({ ...draft, shelf_life_hours: event.target.value })}
              />
            </Field>
            <Field label={t("storageTemperature")} className="sm:col-span-3">
              <Input
                value={draft.storage_temperature}
                onChange={(event) => setDraft({ ...draft, storage_temperature: event.target.value })}
              />
            </Field>
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
          {current && canSeeCosts && current.cost_min !== undefined && current.cost_max !== undefined ? (
            <p className="text-sm text-[var(--ink)]">
              {draft.kind === "weighted"
                ? t("costPerKg", { weight: draft.basis_weight_kg })
                : t("costPerPiece", { count: 1 })}
              :{" "}
              {formatCostRange(
                displayedCost(current.cost_min, current.kind, current.basis_quantity),
                displayedCost(current.cost_max, current.kind, current.basis_quantity),
                (values) => t("costRange", values),
              )}
            </p>
          ) : null}

          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{t("method")}</span>
            <MarkdownEditor value={draft.method} onChange={(method) => setDraft({ ...draft, method })} />
          </div>

          {current ? (
            <MenuImages
              images={current.images}
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
            lines={baseLines(draft)}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={[...sectionOptions(draft.sections, t("section")), ...options]}
            extraColumn="loss"
            quantityLabel={t("quantity")}
            chooseQuantityUnit={true}
            linePrice={null}
            onCreateSuggestion={createSuggestion}
            onCreateIngredient={(line, name) => createIngredient(line, name, line.quantity_unit)}
            suggestionPending={ingredients.save.isPending || semiProducts.save.isPending}
            keepSelectedOnDigit={true}
            quantityRequired={false}
          />

          <CardTitle>{t("sections")}</CardTitle>
          {draft.sections.map((section, index) => (
            <div
              key={section.key}
              data-field-group={tForms("sectionNumber", { number: index + 1 })}
              data-error-list="sections"
              className="grid gap-3 rounded-2xl border border-[var(--line)] p-4"
            >
              <div className="flex items-center gap-2">
                <Input
                  name="name"
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
                    setDraft({
                      ...draft,
                      sections: draft.sections.filter((row) => row.key !== section.key),
                      lines: draft.lines.filter((line) => line.component !== `section:${section.key}`),
                    })
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
                chooseQuantityUnit={true}
                linePrice={null}
                onCreateSuggestion={createSuggestion}
                onCreateIngredient={(line, name) => createIngredient(line, name, line.quantity_unit)}
                suggestionPending={ingredients.save.isPending || semiProducts.save.isPending}
                keepSelectedOnDigit={true}
                quantityRequired={false}
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
                          const lossPercent = line ? lossPercentText(line.quantity, line.loss_quantity) : null;
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
                                  <div
                                    data-field-group={modifier.name}
                                    className="relative ml-auto w-36"
                                  >
                                    <Input
                                      name="quantity"
                                      inputMode="decimal"
                                      placeholder={t("quantity")}
                                      value={line.quantity}
                                      onChange={(event) =>
                                        setComposition(modifier.id, {
                                          lines: [{ ...line, quantity: event.target.value }],
                                        })
                                      }
                                      className="pr-16 text-right"
                                    />
                                    <QuantityUnitControl
                                      option={options.find((row) => row.value === line.component)}
                                      value={line.quantity_unit}
                                      chooseQuantityUnit={true}
                                      onChange={(quantity_unit) =>
                                        setComposition(modifier.id, {
                                          lines: [{ ...line, quantity_unit }],
                                        })
                                      }
                                    />
                                  </div>
                                ) : (
                                  <p className="text-right">—</p>
                                )}
                              </td>
                              <td className="py-2">
                                {line ? (
                                  <div className="ml-auto flex w-44 items-center justify-end gap-2">
                                    <div className="relative min-w-0 flex-1">
                                      <Input
                                        name="loss_quantity"
                                        inputMode="decimal"
                                        placeholder={t("lossPercent")}
                                        value={line.loss_quantity}
                                        onChange={(event) =>
                                          setComposition(modifier.id, {
                                            lines: [{ ...line, loss_quantity: event.target.value }],
                                          })
                                        }
                                        className="pr-10 text-right"
                                      />
                                      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                                        {units(line.quantity_unit)}
                                      </span>
                                    </div>
                                    {lossPercent !== null ? (
                                      <span className="shrink-0 text-xs tabular-nums text-[var(--muted-2)]">{lossPercent}%</span>
                                    ) : null}
                                  </div>
                                ) : null}
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
                    options,
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

      {restoreOpen ? (
        <Dialog open onOpenChange={() => undefined}>
          <DialogContent hideClose className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
            <DialogTitle className="text-lg font-semibold text-[var(--ink)]">{t("restoreDraftTitle")}</DialogTitle>
            <DialogDescription className="mt-2 text-sm text-[var(--muted-2)]">{t("restoreDraftBody")}</DialogDescription>
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={dropStoredDraft}>
                {t("startFresh")}
              </Button>
              <Button type="button" onClick={keepStoredDraft}>
                {t("restoreDraft")}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
