import {
  componentRef,
  componentValue,
  newDraftKey,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
import type { CrmOrderItem, CrmOrderItemBody, CrmOrderItemCostBody, CrmOrderItemLineBody, TechCard } from "@/lib/api/types";

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
      component: componentValue({ ...line, nested_tech_card: line.tech_card }),
      quantity: line.quantity,
      loss_percent: "0",
      unit_cost: "",
      quantity_unit: line.unit,
      suggestion: null,
    })),
  };
}

function orderLineBody(line: ComponentLineDraft, quantity: string): CrmOrderItemLineBody {
  const ref = componentRef(line.component);
  return {
    ingredient: ref.ingredient,
    semi_product: ref.semi_product,
    tech_card: ref.nested_tech_card,
    quantity,
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
    lines: item.lines.map((line) => orderLineBody(line, line.quantity.replace(",", "."))),
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
    lines.push(orderLineBody(line, lineQuantity));
  }
  return {
    tech_card: card.id,
    quantity,
    weight_kg: weight,
    modifiers,
    lines,
  };
}

export function crmItemTitle(item: CrmItemDraft, techCards: TechCard[]): string {
  if (item.name.trim() !== "") return item.name.trim();
  return findCard(techCards, item.tech_card)?.name ?? "";
}

function extraLineSale(line: ComponentLineDraft, techCards: TechCard[]): number {
  const cardId = componentRef(line.component).nested_tech_card;
  if (cardId === null) return 0;
  const card = findCard(techCards, cardId);
  if (card === undefined || card.sale_price === null) return 0;
  const quantity = decimalOrNull(line.quantity);
  if (quantity === null) return 0;
  const net = Number(quantity);
  const sale = Number(card.sale_price);
  if (card.kind === "weighted") {
    if (card.basis_weight_kg === null) return 0;
    return (sale * (net / 1000)) / Number(card.basis_weight_kg);
  }
  return sale * net;
}

function extraLinesSale(item: CrmItemDraft, techCards: TechCard[]): number {
  return item.lines.reduce((extra, line) => extra + extraLineSale(line, techCards), 0);
}

function roundCents(value: number): string {
  return (Math.round(value * 100) / 100).toFixed(2);
}

function surcharge(amount: number): string | null {
  const rounded = roundCents(amount);
  return Number(rounded) === 0 ? null : rounded;
}

function weightFactor(item: CrmItemDraft, card: TechCard): number | null {
  if (card.kind !== "weighted") return 1;
  const weight = decimalOrNull(item.weight_kg);
  if (weight === null || card.basis_weight_kg === null) return null;
  return Number(weight) / Number(card.basis_weight_kg);
}

function modifierSale(item: CrmItemDraft, card: TechCard, techCards: TechCard[], modifierId: number, quantity: number): number {
  const factor = weightFactor(item, card);
  if (factor === null) return 0;
  const row = item.modifiers.find((modifier) => modifier.modifier === modifierId);
  if (row === undefined) return 0;
  const modifierQuantity = Number(row.quantity || "1");
  let extra = 0;
  for (const line of card.modifier_lines) {
    if (line.modifier !== modifierId || line.nested_tech_card === null) continue;
    const nested = findCard(techCards, line.nested_tech_card);
    if (nested === undefined || nested.sale_price === null) continue;
    let scale = modifierQuantity * quantity;
    if (line.scales_by_weight) scale *= factor;
    const net = Number(line.quantity) * scale;
    const sale = Number(nested.sale_price);
    if (nested.kind === "weighted") {
      if (nested.basis_weight_kg === null) continue;
      extra += (sale * (net / 1000)) / Number(nested.basis_weight_kg);
    } else {
      extra += sale * net;
    }
  }
  return extra;
}

function nestedModifierSale(item: CrmItemDraft, card: TechCard, techCards: TechCard[], quantity: number): number {
  return item.modifiers.reduce(
    (extra, row) => extra + modifierSale(item, card, techCards, row.modifier, quantity),
    0,
  );
}

function baseSale(item: CrmItemDraft, card: TechCard): number | null {
  const quantity = Number(item.quantity);
  if (!Number.isInteger(quantity) || quantity < 1 || card.sale_price === null) return null;
  const sale = Number(card.sale_price);
  if (card.kind === "weighted") {
    const weight = decimalOrNull(item.weight_kg);
    if (weight === null || card.basis_weight_kg === null) return null;
    return (sale * Number(weight) * quantity) / Number(card.basis_weight_kg);
  }
  return sale * quantity;
}

export function crmItemBaseSale(item: CrmItemDraft, techCards: TechCard[]): string | null {
  const card = findCard(techCards, item.tech_card);
  if (card === undefined) return null;
  const amount = baseSale(item, card);
  return amount === null ? null : roundCents(amount);
}

export function crmModifierSale(item: CrmItemDraft, techCards: TechCard[], modifierId: number): string | null {
  const card = findCard(techCards, item.tech_card);
  if (card === undefined) return null;
  const quantity = Number(item.quantity);
  if (!Number.isInteger(quantity) || quantity < 1) return null;
  return surcharge(modifierSale(item, card, techCards, modifierId, quantity));
}

export function crmItemSalePrice(item: CrmItemDraft, techCards: TechCard[]): string | null {
  const card = findCard(techCards, item.tech_card);
  if (card === undefined) return null;
  const amount = baseSale(item, card);
  if (amount === null) return null;
  const quantity = Number(item.quantity);
  const extra = nestedModifierSale(item, card, techCards, quantity) + extraLinesSale(item, techCards);
  return roundCents(amount + extra);
}

export function crmItemsPriceSum(items: CrmItemDraft[], techCards: TechCard[]): number {
  return items.reduce((sum, item) => {
    const price = crmItemSalePrice(item, techCards);
    return price === null ? sum : sum + Number(price);
  }, 0);
}
