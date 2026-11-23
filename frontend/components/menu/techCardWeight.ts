import { lineGrams } from "@/components/menu/ui";
import type { TechCard } from "@/lib/api/types";

type WeightLine = TechCard["lines"][number];

function roundGrams(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function amount(value: string | null): number {
  if (value === null || value.trim() === "") return 0;
  const number = Number(value.replace(",", "."));
  return Number.isFinite(number) ? number : 0;
}

export function hasNestedTechCard(
  lines: { nested_tech_card: number | null }[],
  sections: { lines: { nested_tech_card: number | null }[] }[],
): boolean {
  if (lines.some((line) => line.nested_tech_card !== null)) return true;
  return sections.some((section) => section.lines.some((line) => line.nested_tech_card !== null));
}

export function pieceLineGrams(
  quantity: string | null,
  quantityUnit: string,
  nestedTechCard: number | null,
  cards: Map<number, TechCard>,
  gramsPerUnit: (ingredientId: number) => string | null,
): number | null {
  return pieceLineGramsIn(quantity, quantityUnit, nestedTechCard, cards, gramsPerUnit, new Set());
}

function pieceLineGramsIn(
  quantity: string | null,
  quantityUnit: string,
  nestedTechCard: number | null,
  cards: Map<number, TechCard>,
  gramsPerUnit: (ingredientId: number) => string | null,
  path: Set<number>,
): number | null {
  if (nestedTechCard === null || quantityUnit !== "pcs") return null;
  const card = cards.get(nestedTechCard);
  if (card === undefined || card.kind !== "piece") return null;
  if (card.basis_quantity === null || card.basis_quantity === 0) return 0;
  const net = cardNetGrams(card, cards, gramsPerUnit, path);
  return roundGrams((amount(quantity) * net) / card.basis_quantity);
}

function cardNetGrams(
  card: TechCard,
  cards: Map<number, TechCard>,
  gramsPerUnit: (ingredientId: number) => string | null,
  path: Set<number>,
): number {
  if (path.has(card.id)) return 0;
  const nested = new Set(path);
  nested.add(card.id);
  let total = 0;
  for (const line of card.lines) {
    if (line.nested_section !== null) continue;
    total += techCardLineGrams(line, cards, gramsPerUnit, nested);
  }
  for (const section of card.sections) {
    for (const line of section.lines) {
      total += techCardLineGrams(line, cards, gramsPerUnit, nested);
    }
  }
  return total;
}

function techCardLineGrams(
  line: WeightLine,
  cards: Map<number, TechCard>,
  gramsPerUnit: (ingredientId: number) => string | null,
  path: Set<number>,
): number {
  const piece = pieceLineGramsIn(
    line.quantity,
    line.quantity_unit,
    line.nested_tech_card,
    cards,
    gramsPerUnit,
    path,
  );
  if (piece !== null) return piece;
  return lineGrams(
    line.quantity,
    line.quantity_unit,
    line.ingredient === null ? null : gramsPerUnit(line.ingredient),
  );
}
