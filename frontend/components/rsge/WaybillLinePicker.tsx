"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { Ban, History, Plus, Sparkles } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { listPlacement } from "@/components/menu/SearchSelect";
import { formatQuantity } from "@/components/menu/ui";
import type { Ingredient, MenuUnit, WaybillSupplyDraftLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type PickerItem =
  | { kind: "skip"; key: "skip"; fromHistory: boolean }
  | {
      kind: "suggestion";
      key: string;
      ingredientId: string;
      name: string;
      quantity: string;
      unit: MenuUnit;
      source: "history" | "ai";
    }
  | { kind: "aiCreate"; key: string; unit: MenuUnit; factor: string }
  | { kind: "ingredient"; key: string; ingredientId: string; name: string }
  | { kind: "create"; key: "create"; name: string };

function localized(locale: string, original: string, ru: string): string {
  if (locale === "ru" && ru !== "") return ru;
  return original;
}

function scaledQuantity(quantity: string, factor: string): string {
  const product = Number(quantity) * Number(factor);
  return String(Math.round(product * 1000) / 1000);
}

function matches(label: string, needle: string): boolean {
  return needle === "" || label.toLowerCase().includes(needle);
}

function pickerItems(
  line: WaybillSupplyDraftLine,
  ingredients: Ingredient[],
  selectedId: string,
  needle: string,
  createName: string,
): PickerItem[] {
  const items: PickerItem[] = [];
  const pinnedIds = new Set<string>();
  const alias = line.alias;
  items.push({
    kind: "skip",
    key: "skip",
    fromHistory: alias !== null && alias.ignored,
  });
  if (alias !== null && !alias.ignored && alias.ingredient_id !== null && alias.factor !== null) {
    const match = ingredients.find((item) => item.id === alias.ingredient_id);
    if (match !== undefined && matches(match.name, needle)) {
      const ingredientId = String(match.id);
      items.push({
        kind: "suggestion",
        key: `history-${ingredientId}-${alias.factor}`,
        ingredientId,
        name: match.name,
        quantity: scaledQuantity(line.quantity, alias.factor),
        unit: match.unit,
        source: "history",
      });
      pinnedIds.add(ingredientId);
    }
  }
  line.suggestions.forEach((suggestion, index) => {
    if (suggestion.ingredient_id === null) {
      items.push({
        kind: "aiCreate",
        key: `ai-create-${index}`,
        unit: suggestion.unit,
        factor: suggestion.factor,
      });
      return;
    }
    const match = ingredients.find((item) => item.id === suggestion.ingredient_id);
    if (match === undefined || !matches(match.name, needle)) return;
    const ingredientId = String(match.id);
    items.push({
      kind: "suggestion",
      key: `ai-${ingredientId}-${suggestion.factor}-${index}`,
      ingredientId,
      name: match.name,
      quantity: scaledQuantity(line.quantity, suggestion.factor),
      unit: match.unit,
      source: "ai",
    });
    pinnedIds.add(ingredientId);
  });
  for (const item of ingredients) {
    const ingredientId = String(item.id);
    if (pinnedIds.has(ingredientId)) continue;
    if (!item.is_active && ingredientId !== selectedId) continue;
    if (!matches(item.name, needle)) continue;
    items.push({ kind: "ingredient", key: `ingredient-${ingredientId}`, ingredientId, name: item.name });
  }
  if (createName !== "") {
    const exact = ingredients.some((item) => item.name.toLowerCase() === createName.toLowerCase());
    if (!exact) items.push({ kind: "create", key: "create", name: createName });
  }
  return items;
}

export function WaybillLinePicker({
  line,
  ingredientId,
  skipped,
  ingredients,
  onSkip,
  onPick,
  onCreate,
}: {
  line: WaybillSupplyDraftLine;
  ingredientId: string;
  skipped: boolean;
  ingredients: Ingredient[];
  onSkip: () => void;
  onPick: (ingredientId: string, quantity: string | null) => void;
  onCreate: (name: string, unit: MenuUnit, quantity: string | null) => void;
}) {
  const t = useTranslations("rsge");
  const stock = useTranslations("stock");
  const units = useTranslations("stock.units");
  const locale = useLocale();
  const lineName = localized(locale, line.name, line.name_ru);
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingSelect = useRef(false);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [edited, setEdited] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [placement, setPlacement] = useState({ upward: false, maxHeight: 240 });
  const selected = ingredients.find((item) => String(item.id) === ingredientId);
  const selectedLabel = selected === undefined ? "" : selected.name;
  const needle = open && edited ? query.trim().toLowerCase() : "";
  const createName = open && edited ? query.trim() : "";
  const items = pickerItems(line, ingredients, ingredientId, needle, createName).filter((item) => {
    if (item.kind === "skip") return matches(t("skipLine"), needle);
    if (item.kind === "aiCreate") return matches(lineName, needle);
    return true;
  });
  const highlightIndex = items.length === 0 ? 0 : Math.min(highlight, items.length - 1);
  const active = items[highlightIndex] ?? null;

  const close = () => {
    pendingSelect.current = document.activeElement === inputRef.current;
    setOpen(false);
    setEdited(false);
    setQuery("");
  };

  const choose = (item: PickerItem) => {
    if (item.kind === "skip") onSkip();
    else if (item.kind === "suggestion") onPick(item.ingredientId, item.quantity);
    else if (item.kind === "ingredient") onPick(item.ingredientId, null);
    else if (item.kind === "aiCreate") onCreate(lineName, item.unit, scaledQuantity(line.quantity, item.factor));
    else onCreate(item.name, "g", null);
    close();
  };

  const openList = () => {
    const index = skipped
      ? items.findIndex((item) => item.kind === "skip")
      : items.findIndex(
          (item) =>
            (item.kind === "suggestion" || item.kind === "ingredient") && item.ingredientId === ingredientId,
        );
    const fallback = items.findIndex((item) => item.kind !== "skip");
    pendingSelect.current = true;
    setQuery(skipped ? "" : selectedLabel);
    setEdited(false);
    setHighlight(index >= 0 ? index : fallback >= 0 ? fallback : 0);
    setOpen(true);
  };

  useLayoutEffect(() => {
    if (!pendingSelect.current) return;
    pendingSelect.current = false;
    inputRef.current?.select();
  }, [open, query]);

  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!open || !root) return;
    const update = () => {
      const next = listPlacement(root);
      setPlacement((current) =>
        current.upward === next.upward && current.maxHeight === next.maxHeight ? current : next,
      );
    };
    update();
    const scrollers: HTMLElement[] = [];
    let node: HTMLElement | null = root.parentElement;
    while (node) {
      const overflowY = getComputedStyle(node).overflowY;
      if (overflowY === "auto" || overflowY === "scroll" || overflowY === "hidden") scrollers.push(node);
      node = node.parentElement;
    }
    for (const scroller of scrollers) scroller.addEventListener("scroll", update);
    window.addEventListener("resize", update);
    return () => {
      for (const scroller of scrollers) scroller.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const list = listRef.current;
    const item = list?.querySelector(`[data-index="${highlightIndex}"]`);
    if (!list || !(item instanceof HTMLElement)) return;
    const itemTop = item.offsetTop;
    const itemBottom = itemTop + item.offsetHeight;
    if (itemTop < list.scrollTop) list.scrollTop = itemTop;
    else if (itemBottom > list.scrollTop + list.clientHeight) list.scrollTop = itemBottom - list.clientHeight;
  }, [highlightIndex, open, needle]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      const root = rootRef.current;
      if (!root || !(event.target instanceof Node) || root.contains(event.target)) return;
      close();
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const optionClass = (index: number, suggested: boolean) =>
    cn(
      "flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[var(--ink)]",
      suggested
        ? index === highlightIndex
          ? "bg-[var(--brand)]/20"
          : "bg-[var(--brand)]/10 hover:bg-[var(--brand)]/15"
        : index === highlightIndex
          ? "bg-[var(--cream)]"
          : "hover:bg-[var(--cream)]",
    );

  let suggestionHeading = false;
  let ingredientHeading = false;

  return (
    <div
      ref={rootRef}
      className="relative min-w-0"
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (next instanceof Node && rootRef.current?.contains(next)) return;
        close();
      }}
    >
      {skipped ? null : (
        <input
          tabIndex={-1}
          aria-hidden="true"
          required
          value={ingredientId}
          onChange={() => undefined}
          className="pointer-events-none absolute bottom-0 left-5 h-px w-px opacity-0"
        />
      )}
      <input
        ref={inputRef}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && active ? `${listId}-${highlightIndex}` : undefined}
        autoComplete="off"
        placeholder={stock("chooseComponent")}
        value={open ? query : skipped ? t("skipLine") : selectedLabel}
        onChange={(event) => {
          setQuery(event.target.value);
          setEdited(true);
          setHighlight(0);
          setOpen(true);
        }}
        onMouseDown={(event) => {
          if (open) return;
          event.preventDefault();
          event.currentTarget.focus();
          openList();
        }}
        onMouseUp={() => {
          if (!edited) inputRef.current?.select();
        }}
        onFocus={() => {
          if (!open) openList();
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            if (!open) {
              openList();
              return;
            }
            setHighlight(Math.min(highlightIndex + 1, Math.max(items.length - 1, 0)));
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            if (!open) {
              openList();
              return;
            }
            setHighlight((current) => Math.max(current - 1, 0));
            return;
          }
          if (event.key === "Enter" && open) {
            event.preventDefault();
            if (active) choose(active);
            return;
          }
          if (event.key === "Escape" && open) {
            event.preventDefault();
            event.stopPropagation();
            close();
          }
        }}
        className={cn(
          "h-12 w-full rounded-full border border-[var(--line)] bg-white px-5 text-sm text-[var(--ink)] placeholder:text-[var(--muted-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand)]/30",
          !open && skipped && "text-[var(--muted-2)] line-through",
        )}
      />
      {open ? (
        <div
          ref={listRef}
          id={listId}
          role="listbox"
          style={{ maxHeight: placement.maxHeight }}
          className={cn(
            "absolute z-30 w-full overflow-y-auto rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg",
            placement.upward ? "bottom-full mb-1" : "top-full mt-1",
          )}
        >
          {items.length === 0 ? (
            <p className="px-4 py-2 text-sm text-[var(--muted-2)]">{stock("noMatches")}</p>
          ) : (
            items.map((item, index) => {
              const suggested = item.kind === "suggestion" || item.kind === "aiCreate";
              const showSuggestionHeading = suggested && !suggestionHeading;
              const showIngredientHeading = item.kind === "ingredient" && !ingredientHeading;
              if (showSuggestionHeading) suggestionHeading = true;
              if (showIngredientHeading) ingredientHeading = true;
              return (
                <div key={item.key}>
                  {showSuggestionHeading ? (
                    <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--brand)]">
                      {t("suggestionsHeading")}
                    </p>
                  ) : null}
                  {showIngredientHeading ? (
                    <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
                      {t("allIngredients")}
                    </p>
                  ) : null}
                  {item.kind === "skip" ? (
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={skipped}
                      data-index={index}
                      tabIndex={-1}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setHighlight(index)}
                      onClick={() => choose(item)}
                      className={optionClass(index, false)}
                    >
                      <Ban className="h-4 w-4 shrink-0 text-[var(--muted-2)]" />
                      <span className="min-w-0 flex-1 truncate text-[var(--muted-2)]">{t("skipLine")}</span>
                      {item.fromHistory ? (
                        <span className="shrink-0 rounded-full bg-[var(--cream)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)]">
                          {t("fromHistory")}
                        </span>
                      ) : null}
                    </button>
                  ) : null}
                  {item.kind === "suggestion" ? (
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={item.ingredientId === ingredientId}
                      data-index={index}
                      tabIndex={-1}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setHighlight(index)}
                      onClick={() => choose(item)}
                      className={optionClass(index, true)}
                    >
                      {item.source === "ai" ? (
                        <Sparkles className="h-4 w-4 shrink-0 text-[var(--brand)]" />
                      ) : (
                        <History className="h-4 w-4 shrink-0 text-[var(--brand)]" />
                      )}
                      <span className="min-w-0 flex-1 truncate font-medium">{item.name}</span>
                      <span className="shrink-0 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--brand)]">
                        {item.source === "ai" ? t("fromAi") : t("fromHistory")}
                      </span>
                      <span className="shrink-0 text-xs font-semibold text-[var(--brand)]">
                        {formatQuantity(item.quantity)} {units(item.unit)}
                      </span>
                    </button>
                  ) : null}
                  {item.kind === "aiCreate" ? (
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={false}
                      data-index={index}
                      tabIndex={-1}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setHighlight(index)}
                      onClick={() => choose(item)}
                      className={optionClass(index, true)}
                    >
                      <Sparkles className="h-4 w-4 shrink-0 text-[var(--brand)]" />
                      <span className="min-w-0 flex-1 truncate">
                        <span className="block truncate font-medium">{lineName}</span>
                        <span className="block text-xs text-[var(--brand)]">{t("aiCreateNew")}</span>
                      </span>
                      <span className="shrink-0 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--brand)]">
                        {t("fromAi")}
                      </span>
                      <span className="shrink-0 text-xs font-semibold text-[var(--brand)]">{units(item.unit)}</span>
                    </button>
                  ) : null}
                  {item.kind === "ingredient" ? (
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={item.ingredientId === ingredientId}
                      data-index={index}
                      tabIndex={-1}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setHighlight(index)}
                      onClick={() => choose(item)}
                      className={cn(optionClass(index, false), item.ingredientId === ingredientId && "font-semibold")}
                    >
                      <span className="min-w-0 flex-1 truncate">{item.name}</span>
                    </button>
                  ) : null}
                  {item.kind === "create" ? (
                    <button
                      id={`${listId}-${index}`}
                      type="button"
                      role="option"
                      aria-selected={false}
                      data-index={index}
                      tabIndex={-1}
                      onMouseDown={(event) => event.preventDefault()}
                      onMouseEnter={() => setHighlight(index)}
                      onClick={() => choose(item)}
                      className={cn(optionClass(index, false), "border-t border-[var(--line)]")}
                    >
                      <Plus className="h-4 w-4 shrink-0 text-[var(--brand)]" />
                      <span className="min-w-0 flex-1 truncate font-medium text-[var(--brand)]">
                        {t("createNamed", { name: item.name })}
                      </span>
                    </button>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      ) : null}
    </div>
  );
}
