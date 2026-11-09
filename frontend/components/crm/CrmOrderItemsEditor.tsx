"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Check, MessageSquare, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { NativeSelect } from "@/components/menu/ui";
import { useCrmItemCost } from "@/hooks/useCrmOrders";
import { useTechCards } from "@/hooks/useStock";
import type { TechCard, TechCardGroup } from "@/lib/api/types";
import {
  crmItemBaseSale,
  crmItemCostBody,
  crmItemSalePrice,
  crmItemTitle,
  crmModifierSale,
  emptyCrmItem,
  type CrmItemDraft,
  type CrmItemModifierDraft,
} from "@/lib/crmItems";
import { formatAed } from "@/lib/format";
import { cn } from "@/lib/utils";

function measureText(item: CrmItemDraft, card: TechCard | undefined, kg: string, pcs: string): string {
  const quantity = item.quantity.trim() === "" ? "1" : item.quantity;
  if (card?.kind === "weighted" && item.weight_kg.trim() !== "") {
    return `${item.weight_kg} ${kg} × ${quantity}`;
  }
  return `${quantity} ${pcs}`;
}

function modifierText(item: CrmItemDraft, card: TechCard | undefined): string {
  if (card === undefined) return "";
  const names: string[] = [];
  for (const row of item.modifiers) {
    for (const group of card.modifier_groups) {
      const modifier = group.modifiers.find((option) => option.id === row.modifier);
      if (modifier === undefined) continue;
      const quantity = Number(row.quantity || "1");
      names.push(quantity > 1 ? `${modifier.name} × ${quantity}` : modifier.name);
    }
  }
  return names.join(", ");
}

function SingleModifier({
  group,
  selected,
  modifierPrice,
  required,
  onChange,
}: {
  group: TechCardGroup;
  selected: CrmItemModifierDraft[];
  modifierPrice: (modifierId: number) => string | null;
  required: boolean;
  onChange: (rows: CrmItemModifierDraft[]) => void;
}) {
  const t = useTranslations("crm.items");
  const ids = new Set(group.modifiers.map((modifier) => modifier.id));
  const inGroup = selected.filter((row) => ids.has(row.modifier));
  const others = selected.filter((row) => !ids.has(row.modifier));
  const current = inGroup[0];
  const price = current === undefined ? null : modifierPrice(current.modifier);
  const label = `${group.group_name}${group.effective_is_required ? " *" : ""}`;
  return (
    <>
      <NativeSelect
        required={required}
        aria-label={label}
        value={current ? String(current.modifier) : ""}
        onChange={(event) =>
          onChange(
            event.target.value === ""
              ? others
              : [
                  ...others,
                  {
                    modifier: Number(event.target.value),
                    quantity: current === undefined ? "1" : current.quantity,
                  },
                ],
          )
        }
        className="h-9 w-auto max-w-40 px-3"
      >
        <option value="">{label}</option>
        {group.modifiers.map((modifier) => (
          <option key={modifier.id} value={modifier.id}>
            {modifier.name}
          </option>
        ))}
      </NativeSelect>
      {current ? (
        <Input
          name="quantity"
          required
          inputMode="numeric"
          aria-label={t("modifierQuantity")}
          value={current.quantity}
          onChange={(event) =>
            onChange([
              ...others,
              ...inGroup.map((row) =>
                row.modifier === current.modifier ? { ...row, quantity: event.target.value } : row,
              ),
            ])
          }
          className="h-9 w-14 px-2 text-center"
        />
      ) : null}
      {price !== null ? (
        <span className="text-xs font-medium tabular-nums text-[var(--ink)]">{formatAed(price)}</span>
      ) : null}
    </>
  );
}

function MultiModifiers({
  group,
  selected,
  modifierPrice,
  onChange,
}: {
  group: TechCardGroup;
  selected: CrmItemModifierDraft[];
  modifierPrice: (modifierId: number) => string | null;
  onChange: (rows: CrmItemModifierDraft[]) => void;
}) {
  const t = useTranslations("crm.items");
  const ids = new Set(group.modifiers.map((modifier) => modifier.id));
  const inGroup = selected.filter((row) => ids.has(row.modifier));
  const others = selected.filter((row) => !ids.has(row.modifier));
  const label = `${group.group_name}${group.effective_is_required ? " *" : ""}`;
  const setQuantity = (modifier: number, quantity: string) =>
    onChange([...others, ...inGroup.map((row) => (row.modifier === modifier ? { ...row, quantity } : row))]);
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-[var(--ink)]/60">{label}</span>
      {group.modifiers.map((modifier) => {
        const row = inGroup.find((item) => item.modifier === modifier.id);
        const price = row === undefined ? null : modifierPrice(modifier.id);
        return (
          <div
            key={modifier.id}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm",
              row ? "border-[var(--brand)] bg-[var(--cream)]" : "border-[var(--line)]",
            )}
          >
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={row !== undefined}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...selected, { modifier: modifier.id, quantity: "1" }]
                      : selected.filter((item) => item.modifier !== modifier.id),
                  )
                }
                className="h-4 w-4 accent-[var(--brand)]"
              />
              {modifier.name}
            </label>
            {row ? (
              <Input
                name="quantity"
                required
                inputMode="numeric"
                aria-label={t("modifierQuantity")}
                value={row.quantity}
                onChange={(event) => setQuantity(modifier.id, event.target.value)}
                className="h-7 w-12 px-1 text-center"
              />
            ) : null}
            {price !== null ? <span className="tabular-nums text-[var(--ink)]">{formatAed(price)}</span> : null}
          </div>
        );
      })}
    </div>
  );
}

function ItemComposer({
  item,
  number,
  errors,
  techCards,
  listed,
  onChange,
  onCommit,
  onRemove,
}: {
  item: CrmItemDraft;
  number: number;
  errors: string[];
  techCards: TechCard[];
  listed: boolean;
  onChange: (item: CrmItemDraft) => void;
  onCommit: () => void;
  onRemove: () => void;
}) {
  const t = useTranslations("crm.items");
  const rowRef = useRef<HTMLDivElement>(null);
  const [commentOpen, setCommentOpen] = useState(item.comment !== "");
  const card = item.tech_card === null ? undefined : techCards.find((row) => row.id === item.tech_card);
  const cardOptions = techCards
    .filter((row) => row.is_active || row.id === item.tech_card)
    .map((row) => ({ value: String(row.id), label: row.name }));
  const cost = useCrmItemCost(card === undefined ? null : crmItemCostBody(item, card));
  const price = crmItemBaseSale(item, techCards);
  const update = (patch: Partial<CrmItemDraft>) => onChange({ ...item, ...patch });

  const commit = () => {
    const root = rowRef.current;
    if (root === null) return;
    if (item.tech_card === null) {
      root.querySelector<HTMLInputElement>('input[role="combobox"]')?.focus();
      return;
    }
    const fields = root.querySelectorAll<HTMLInputElement | HTMLSelectElement>("input, select");
    for (const field of fields) {
      if (!field.checkValidity()) {
        field.reportValidity();
        return;
      }
    }
    onCommit();
  };

  return (
    <div
      ref={rowRef}
      data-field-group={listed ? t("itemNumber", { number }) : undefined}
      data-error-list={listed ? "items" : undefined}
      onKeyDown={(event) => {
        if (event.key !== "Enter" || event.defaultPrevented) return;
        if (event.target instanceof HTMLElement && event.target.closest("button")) return;
        event.preventDefault();
        commit();
      }}
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-2xl border px-2 py-2",
        errors.length > 0
          ? "border-[var(--danger)] bg-red-50"
          : item.needs_review
            ? "border-amber-300 bg-amber-50"
            : "border-[var(--line)]",
      )}
    >
      {item.needs_review ? <TriangleAlert className="h-4 w-4 shrink-0 text-amber-700" /> : null}
      <SearchSelect
        options={cardOptions}
        value={item.tech_card === null ? "" : String(item.tech_card)}
        onChange={(value) => {
          const techCardId = Number(value);
          const nextCard = techCards.find((row) => row.id === techCardId);
          update({
            tech_card: techCardId,
            modifiers: [],
            name: "",
            weight_kg:
              nextCard !== undefined && nextCard.kind === "weighted" ? (nextCard.basis_weight_kg ?? "") : "",
          });
        }}
        placeholder={t("chooseTechCard")}
        required={listed}
        name="tech_card"
        className="min-w-0 basis-full sm:basis-64 sm:flex-1"
      />
      {card?.kind === "weighted" ? (
        <Input
          name="weight_kg"
          required={listed}
          inputMode="decimal"
          aria-label={t("weightKg")}
          placeholder={t("kg")}
          value={item.weight_kg}
          onChange={(event) => update({ weight_kg: event.target.value })}
          className="h-9 w-20 px-3"
        />
      ) : null}
      <Input
        name="quantity"
        required={listed}
        inputMode="numeric"
        aria-label={t("quantity")}
        placeholder={t("pcs")}
        value={item.quantity}
        onChange={(event) => update({ quantity: event.target.value })}
        className="h-9 w-14 px-2 text-center"
      />
      {card?.modifier_groups.map((group) =>
        group.selection_type === "single" ? (
          <SingleModifier
            key={group.group}
            group={group}
            selected={item.modifiers}
            modifierPrice={(modifierId) => crmModifierSale(item, techCards, modifierId)}
            required={listed && group.effective_is_required}
            onChange={(modifiers) => update({ modifiers })}
          />
        ) : (
          <MultiModifiers
            key={group.group}
            group={group}
            selected={item.modifiers}
            modifierPrice={(modifierId) => crmModifierSale(item, techCards, modifierId)}
            onChange={(modifiers) => update({ modifiers })}
          />
        ),
      )}
      {card !== undefined ? (
        <span className="flex items-center gap-2 text-xs font-medium tabular-nums text-[var(--ink)]">
          <span>{price === null ? "—" : formatAed(price)}</span>
          {card.sale_price === null ? <span className="text-amber-700">{t("noSalePrice")}</span> : null}
          {cost.data !== undefined ? (
            <span>{t("foodCost", { value: Number(cost.data).toFixed(2) })}</span>
          ) : null}
        </span>
      ) : null}
      {commentOpen ? (
        <Input
          value={item.comment}
          placeholder={t("comment")}
          aria-label={t("comment")}
          onChange={(event) => update({ comment: event.target.value })}
          className="h-9 w-40 px-3"
        />
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={t("editComment")}
        aria-pressed={commentOpen}
        onClick={() => setCommentOpen((open) => !open)}
        className="h-9 w-9"
      >
        <MessageSquare className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={t("commitItem")}
        onClick={commit}
        className="h-9 w-9"
      >
        <Check className="h-4 w-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={t("removeItem")}
        onClick={onRemove}
        className="h-9 w-9"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
      {errors.length > 0 ? (
        <div className="grid basis-full gap-1">
          {errors.map((message, index) => (
            <p key={index} className="text-sm font-medium text-[var(--danger)]">
              {message}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ItemRow({
  item,
  number,
  errors,
  techCards,
  onEdit,
  onRemove,
}: {
  item: CrmItemDraft;
  number: number;
  errors: string[];
  techCards: TechCard[];
  onEdit: () => void;
  onRemove: () => void;
}) {
  const t = useTranslations("crm.items");
  const card = item.tech_card === null ? undefined : techCards.find((row) => row.id === item.tech_card);
  const title = crmItemTitle(item, techCards);
  const modifiers = modifierText(item, card);
  const price = crmItemSalePrice(item, techCards);
  return (
    <div
      data-field-group={t("itemNumber", { number })}
      data-error-list="items"
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-2xl border px-3 py-2",
        errors.length > 0
          ? "border-[var(--danger)] bg-red-50"
          : item.needs_review
            ? "border-amber-300 bg-amber-50"
            : "border-[var(--line)]",
      )}
    >
      <button type="button" onClick={onEdit} className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1 text-left text-sm">
        <span className="shrink-0 text-[var(--muted-2)]">{number}</span>
        {item.needs_review ? (
          <TriangleAlert className="h-4 w-4 shrink-0 text-amber-700" aria-label={t("needsReview")} />
        ) : null}
        <span className="truncate font-medium text-[var(--ink)]">{title === "" ? "—" : title}</span>
        <span className="shrink-0 text-[var(--ink)]/70">{measureText(item, card, t("kg"), t("pcs"))}</span>
        {modifiers !== "" ? <span className="truncate text-[var(--ink)]/70">{modifiers}</span> : null}
        {item.comment.trim() !== "" ? <MessageSquare className="h-4 w-4 shrink-0 text-[var(--ink)]/50" /> : null}
        <span className="ml-auto shrink-0 font-medium tabular-nums text-[var(--ink)]">
          {price === null ? "—" : formatAed(price)}
        </span>
      </button>
      <Button type="button" variant="ghost" size="icon" aria-label={t("removeItem")} onClick={onRemove} className="h-9 w-9">
        <Trash2 className="h-4 w-4" />
      </Button>
      {errors.length > 0 ? (
        <div className="grid basis-full gap-1">
          {errors.map((message, index) => (
            <p key={index} className="text-sm font-medium text-[var(--danger)]">
              {message}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function CrmOrderItemsEditor({
  items,
  itemErrors,
  onChange,
}: {
  items: CrmItemDraft[];
  itemErrors: string[][];
  onChange: (items: CrmItemDraft[]) => void;
}) {
  const t = useTranslations("crm.items");
  const techCards = useTechCards();
  const cards = techCards.list.data ?? [];
  const rootRef = useRef<HTMLDivElement>(null);
  const focusTechCard = useRef(false);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<CrmItemDraft>(() => emptyCrmItem());

  useEffect(() => {
    if (!focusTechCard.current) return;
    focusTechCard.current = false;
    rootRef.current?.querySelector<HTMLInputElement>('input[role="combobox"]')?.focus();
  }, [activeKey]);

  const write = (next: CrmItemDraft) => {
    if (items.some((row) => row.key === next.key)) {
      onChange(items.map((row) => (row.key === next.key ? next : row)));
      return;
    }
    if (next.tech_card === null) {
      setDraft(next);
      return;
    }
    onChange([...items, next]);
    setActiveKey(next.key);
    setDraft(emptyCrmItem());
  };

  const commit = (item: CrmItemDraft) => {
    const next = { ...item, needs_review: false };
    if (items.some((row) => row.key === next.key)) {
      onChange(items.map((row) => (row.key === next.key ? next : row)));
    } else if (next.tech_card !== null) {
      onChange([...items, next]);
    }
    setDraft(emptyCrmItem());
    setActiveKey(null);
    focusTechCard.current = true;
  };

  const remove = (key: string) => {
    onChange(items.filter((row) => row.key !== key));
    if (activeKey === key) setActiveKey(null);
  };

  return (
    <div ref={rootRef} className="grid gap-2">
      <p className="text-xs text-[var(--muted-2)]">{t("hint")}</p>
      {items.map((item, index) =>
        item.key === activeKey ? (
          <ItemComposer
            key={item.key}
            item={item}
            number={index + 1}
            errors={itemErrors[index] ?? []}
            techCards={cards}
            listed={true}
            onChange={write}
            onCommit={() => commit(item)}
            onRemove={() => remove(item.key)}
          />
        ) : (
          <ItemRow
            key={item.key}
            item={item}
            number={index + 1}
            errors={itemErrors[index] ?? []}
            techCards={cards}
            onEdit={() => setActiveKey(item.key)}
            onRemove={() => remove(item.key)}
          />
        ),
      )}
      {activeKey === null ? (
        <ItemComposer
          key={draft.key}
          item={draft}
          number={items.length + 1}
          errors={[]}
          techCards={cards}
          listed={false}
          onChange={write}
          onCommit={() => commit(draft)}
          onRemove={() => setDraft(emptyCrmItem())}
        />
      ) : null}
    </div>
  );
}
