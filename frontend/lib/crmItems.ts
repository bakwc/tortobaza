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
    price: crmItemSalePrice(item, techCards),
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

function roundCents(value: number): string {
  return (Math.round(value * 100) / 100).toFixed(2);
}

function nestedModifierSale(item: CrmItemDraft, card: TechCard, techCards: TechCard[], quantity: number): number {
  let weightFactor = 1;
  if (card.kind === "weighted") {
    const weight = decimalOrNull(item.weight_kg);
    if (weight === null || card.basis_weight_kg === null) return 0;
    weightFactor = Number(weight) / Number(card.basis_weight_kg);
  }
  let extra = 0;
  for (const row of item.modifiers) {
    const modifierQuantity = Number(row.quantity || "1");
    for (const line of card.modifier_lines) {
      if (line.modifier !== row.modifier || line.nested_tech_card === null) continue;
      const nested = findCard(techCards, line.nested_tech_card);
      if (nested === undefined || nested.sale_price === null) continue;
      let factor = modifierQuantity * quantity;
      if (line.scales_by_weight) factor *= weightFactor;
      const net = Number(line.quantity) * factor;
      const sale = Number(nested.sale_price);
      if (nested.kind === "weighted") {
        if (nested.basis_weight_kg === null) continue;
        extra += (sale * (net / 1000)) / Number(nested.basis_weight_kg);
      } else {
        extra += sale * net;
      }
    }
  }
  return extra;
}

export function crmItemSalePrice(item: CrmItemDraft, techCards: TechCard[]): string | null {
  const card = findCard(techCards, item.tech_card);
  if (card === undefined || card.sale_price === null) return null;
  const quantity = Number(item.quantity);
  if (!Number.isInteger(quantity) || quantity < 1) return null;
  const sale = Number(card.sale_price);
  const extra = nestedModifierSale(item, card, techCards, quantity);
  if (card.kind === "weighted") {
    const weight = decimalOrNull(item.weight_kg);
    if (weight === null || card.basis_weight_kg === null) return null;
    return roundCents((sale * Number(weight) * quantity) / Number(card.basis_weight_kg) + extra);
  }
  return roundCents(sale * quantity + extra);
}

export function crmItemsPriceSum(items: CrmItemDraft[], techCards: TechCard[]): number {
  return items.reduce((sum, item) => {
    const price = crmItemSalePrice(item, techCards);
    return price === null ? sum : sum + Number(price);
  }, 0);
}
