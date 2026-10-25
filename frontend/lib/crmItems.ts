import {
  componentRef,
  componentValue,
  newDraftKey,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
import type { CrmOrderItem, CrmOrderItemBody, CrmOrderItemCostBody, TechCard } from "@/lib/api/types";

export type CrmItemModifierDraft = { modifier: number; quantity: string };

export type CrmItemDraft = {
  key: string;
  tech_card: number | null;
  name: string;
  quantity: string;
  weight_kg: string;
  price: string;
  comment: string;
  needs_review: boolean;
  modifiers: CrmItemModifierDraft[];
  lines: ComponentLineDraft[];
};

export type CrmItemsTextLabels = { kg: string; pcs: string };

export function emptyCrmItem(): CrmItemDraft {
  return {
    key: newDraftKey(),
    tech_card: null,
    name: "",
    quantity: "1",
    weight_kg: "",
    price: "",
    comment: "",
    needs_review: false,
    modifiers: [],
    lines: [],
  };
}

export function crmItemDraftFromItem(item: CrmOrderItem): CrmItemDraft {
  return {
    key: newDraftKey(),
    tech_card: item.tech_card,
    name: item.name,
    quantity: String(item.quantity),
    weight_kg: item.weight_kg ?? "",
    price: item.price ?? "",
    comment: item.comment,
    needs_review: item.needs_review,
    modifiers: item.modifiers.map((row) => ({ modifier: row.modifier, quantity: String(row.quantity) })),
    lines: item.lines.map((line) => ({
      key: newDraftKey(),
      component: componentValue(line),
      quantity: line.quantity,
      loss_percent: "0",
      unit_cost: "",
      quantity_unit: line.unit,
    })),
  };
}

function decimalOrNull(value: string): string | null {
  const trimmed = value.trim().replace(",", ".");
  return trimmed === "" ? null : trimmed;
}

function findCard(techCards: TechCard[], id: number | null): TechCard | undefined {
  return id === null ? undefined : techCards.find((card) => card.id === id);
}

export function crmItemBody(item: CrmItemDraft, techCards: TechCard[]): CrmOrderItemBody {
  const card = findCard(techCards, item.tech_card);
  return {
    tech_card: item.tech_card,
    name: "",
    quantity: Number(item.quantity || "1"),
    weight_kg: card?.kind === "weighted" ? decimalOrNull(item.weight_kg) : null,
    price: decimalOrNull(item.price),
    comment: item.comment,
    needs_review: item.needs_review,
    modifiers: item.modifiers.map((row) => ({ modifier: row.modifier, quantity: Number(row.quantity || "1") })),
    lines: item.lines.map((line) => ({
      ...componentRef(line.component),
      quantity: line.quantity.replace(",", "."),
    })),
  };
}

export function crmItemCostBody(item: CrmItemDraft, card: TechCard): CrmOrderItemCostBody | null {
  const quantity = Number(item.quantity);
  if (!Number.isInteger(quantity) || quantity < 1) return null;
  const weight = card.kind === "weighted" ? decimalOrNull(item.weight_kg) : null;
  if (card.kind === "weighted" && weight === null) return null;
  const modifiers: { modifier: number; quantity: number }[] = [];
  for (const row of item.modifiers) {
    const modifierQuantity = Number(row.quantity);
    if (!Number.isInteger(modifierQuantity) || modifierQuantity < 1) return null;
    modifiers.push({ modifier: row.modifier, quantity: modifierQuantity });
  }
  const lines: CrmOrderItemCostBody["lines"] = [];
  for (const line of item.lines) {
    const lineQuantity = decimalOrNull(line.quantity);
    if (line.component === "" || lineQuantity === null) return null;
    lines.push({ ...componentRef(line.component), quantity: lineQuantity });
  }
  return {
    tech_card: card.id,
    quantity,
    weight_kg: weight,
    modifiers,
    lines,
  };
}

function formatNumber(value: string): string {
  return String(Number(value.replace(",", "."))).replace(".", ",");
}

export function crmItemTitle(item: CrmItemDraft, techCards: TechCard[]): string {
  if (item.name.trim() !== "") return item.name.trim();
  return findCard(techCards, item.tech_card)?.name ?? "";
}

export function crmItemsWeightText(
  items: CrmItemDraft[],
  techCards: TechCard[],
  labels: CrmItemsTextLabels,
): string {
  const parts: string[] = [];
  for (const item of items) {
    const card = findCard(techCards, item.tech_card);
    if (card === undefined) continue;
    const quantity = Number(item.quantity || "1");
    const prefix = quantity > 1 ? `${quantity} × ` : "";
    if (card.kind === "weighted" && item.weight_kg.trim() !== "") {
      parts.push(`${prefix}${formatNumber(item.weight_kg)} ${labels.kg}`);
    } else if (card.kind === "piece") {
      parts.push(`${quantity} ${labels.pcs}`);
    }
  }
  return parts.join(" + ");
}

export function crmItemsFillingText(items: CrmItemDraft[], techCards: TechCard[]): string {
  const names: string[] = [];
  for (const item of items) {
    const card = findCard(techCards, item.tech_card);
    if (!card) continue;
    for (const row of item.modifiers) {
      for (const group of card.modifier_groups) {
        const modifier = group.modifiers.find((option) => option.id === row.modifier);
        if (!modifier) continue;
        const quantity = Number(row.quantity || "1");
        names.push(quantity > 1 ? `${modifier.name} × ${quantity}` : modifier.name);
      }
    }
  }
  return names.join(", ");
}

export function crmItemsPriceSum(items: CrmItemDraft[]): number | null {
  const prices = items
    .map((item) => decimalOrNull(item.price))
    .filter((value): value is string => value !== null);
  if (prices.length === 0) return null;
  return prices.reduce((sum, value) => sum + Number(value), 0);
}
