"use client";

import { useTranslations } from "next-intl";
import { Plus, Trash2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ComponentLinesEditor, componentOptions } from "@/components/menu/ComponentLinesEditor";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { Field, NativeSelect } from "@/components/menu/ui";
import { GroupPicker } from "@/components/crm/GroupPicker";
import { useCrmItemCost } from "@/hooks/useCrmOrders";
import { useIngredients, useSemiProducts, useTechCards } from "@/hooks/useStock";
import type { TechCard } from "@/lib/api/types";
import { crmItemCostBody, emptyCrmItem, type CrmItemDraft } from "@/lib/crmItems";
import { cn } from "@/lib/utils";

function ItemEditor({
  item,
  techCards,
  onChange,
  onRemove,
}: {
  item: CrmItemDraft;
  techCards: TechCard[];
  onChange: (item: CrmItemDraft) => void;
  onRemove: () => void;
}) {
  const t = useTranslations("crm.items");
  const tStock = useTranslations("stock");
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const card = item.tech_card === null ? undefined : techCards.find((row) => row.id === item.tech_card);
  const techCardOptions = techCards
    .filter((row) => row.is_active || row.id === item.tech_card)
    .map((row) => ({ value: String(row.id), label: row.name }));
  const update = (patch: Partial<CrmItemDraft>) => onChange({ ...item, ...patch, needs_review: false });
  const cost = useCrmItemCost(card === undefined ? null : crmItemCostBody(item, card));
  const options = componentOptions(
    ingredients.list.data ?? [],
    semiProducts.list.data ?? [],
    "all",
    tStock("ingredient"),
    tStock("semiProduct"),
  );

  return (
    <div
      className={cn(
        "grid gap-4 rounded-2xl border p-4",
        item.needs_review ? "border-amber-300 bg-amber-50" : "border-[var(--line)]",
      )}
    >
      {item.needs_review ? (
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-medium text-amber-900">
          <span className="inline-flex items-center gap-1.5">
            <TriangleAlert className="h-4 w-4" />
            {t("needsReview")}
          </span>
          <Button type="button" variant="outline" size="sm" onClick={() => update({})}>
            {t("markReviewed")}
          </Button>
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
        <Field label={t("techCard")}>
          <SearchSelect
            options={techCardOptions}
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
            required={true}
            className=""
          />
        </Field>
        <div className="flex items-end">
          <Button type="button" variant="ghost" size="icon" aria-label={t("removeItem")} onClick={onRemove}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {card?.kind === "weighted" ? (
          <Field label={t("weightKg")}>
            <Input
              required
              inputMode="decimal"
              value={item.weight_kg}
              onChange={(event) => update({ weight_kg: event.target.value })}
            />
          </Field>
        ) : null}
        <Field label={t("quantity")}>
          <Input
            required
            inputMode="numeric"
            value={item.quantity}
            onChange={(event) => update({ quantity: event.target.value })}
          />
        </Field>
        <Field label={t("price")}>
          <Input inputMode="decimal" value={item.price} onChange={(event) => update({ price: event.target.value })} />
          {cost.data !== undefined ? (
            <span className="text-sm font-medium text-[var(--ink)]">
              {t("foodCost", { value: Number(cost.data).toFixed(2) })}
            </span>
          ) : null}
        </Field>
      </div>
      {card && card.modifier_groups.length > 0 ? (
        <div className="grid gap-4">
          {card.modifier_groups.map((group) => (
            <GroupPicker
              key={group.id}
              group={group}
              selected={item.modifiers}
              onChange={(modifiers) => update({ modifiers })}
            />
          ))}
        </div>
      ) : null}
      <div className="grid gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
          {card ? t("extraIngredients") : t("ingredients")}
        </span>
        <ComponentLinesEditor
          lines={item.lines}
          onChange={(lines) => update({ lines })}
          options={options}
          extraColumn={null}
          quantityLabel={t("quantity")}
          chooseQuantityUnit={false}
        />
      </div>
      <Field label={t("comment")}>
        <Input value={item.comment} onChange={(event) => update({ comment: event.target.value })} />
      </Field>
    </div>
  );
}

export function CrmOrderItemsEditor({
  items,
  onChange,
}: {
  items: CrmItemDraft[];
  onChange: (items: CrmItemDraft[]) => void;
}) {
  const t = useTranslations("crm.items");
  const techCards = useTechCards();
  const cards = techCards.list.data ?? [];

  return (
    <div className="grid gap-3">
      <p className="text-xs text-[var(--muted-2)]">{t("hint")}</p>
      {items.map((item) => (
        <ItemEditor
          key={item.key}
          item={item}
          techCards={cards}
          onChange={(next) => onChange(items.map((row) => (row.key === item.key ? next : row)))}
          onRemove={() => onChange(items.filter((row) => row.key !== item.key))}
        />
      ))}
      <div>
        <Button type="button" variant="outline" size="sm" onClick={() => onChange([...items, emptyCrmItem()])}>
          <Plus className="mr-1 h-4 w-4" />
          {t("addItem")}
        </Button>
      </div>
    </div>
  );
}
