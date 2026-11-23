import type { MenuUnit, SemiProduct, TechCard } from "@/lib/api/types";

export type TechCardLine = TechCard["lines"][number];

export type ExpandedChapter = {
  key: string;
  name: string;
  quantity: string | null;
  quantityUnit: MenuUnit | null;
  lines: TechCardLine[];
  method: string;
};

type Opened = {
  token: string;
  factor: number;
  lines: TechCardLine[];
  sections: { id: number; name: string; method: string; lines: TechCardLine[] }[];
  method: string;
};

type Catalogs = {
  techCards: Map<number, TechCard>;
  semiProducts: Map<number, SemiProduct>;
};

function amount(value: string): number {
  return Number(value.replace(",", "."));
}

function formatQty(value: number): string {
  return String(Math.round(value * 1000) / 1000);
}

function scaleLine(line: TechCardLine, factor: number): TechCardLine {
  if (factor === 1) return line;
  const scaled: TechCardLine = {
    ...line,
    quantity: line.quantity === null ? null : formatQty(amount(line.quantity) * factor),
    loss_quantity: formatQty(amount(line.loss_quantity) * factor),
  };
  if (line.cost !== undefined) {
    scaled.cost = (amount(line.cost) * factor).toFixed(2);
  }
  return scaled;
}

function grossInUnit(line: TechCardLine, unit: MenuUnit): number | null {
  if (line.quantity === null || line.quantity_unit !== unit) return null;
  return amount(line.quantity) + amount(line.loss_quantity);
}

function semiFactor(line: TechCardLine, semi: SemiProduct): number | null {
  const used = grossInUnit(line, semi.unit);
  if (used === null) return null;
  const yieldQuantity = amount(semi.yield_quantity);
  if (yieldQuantity === 0) return null;
  return used / yieldQuantity;
}

function techCardFactor(line: TechCardLine, card: TechCard): number | null {
  if (card.kind === "weighted") {
    if (card.basis_weight_kg === null) return null;
    const used = grossInUnit(line, "g");
    if (used === null) return null;
    const basis = amount(card.basis_weight_kg) * 1000;
    if (basis === 0) return null;
    return used / basis;
  }
  if (card.basis_quantity === null || card.basis_quantity === 0) return null;
  const used = grossInUnit(line, "pcs");
  if (used === null) return null;
  return used / card.basis_quantity;
}

function semiLines(semi: SemiProduct): TechCardLine[] {
  return semi.lines.map((line) => ({
    ...line,
    nested_tech_card: null,
    nested_section: null,
  }));
}

function open(line: TechCardLine, catalogs: Catalogs, path: Set<string>): Opened | null {
  if (line.nested_tech_card !== null) {
    const token = `tech:${line.nested_tech_card}`;
    if (path.has(token)) return null;
    const card = catalogs.techCards.get(line.nested_tech_card);
    if (card === undefined) return null;
    const factor = techCardFactor(line, card);
    if (factor === null) return null;
    return { token, factor, lines: card.lines, sections: card.sections, method: card.method };
  }
  if (line.semi_product !== null) {
    const token = `semi:${line.semi_product}`;
    if (path.has(token)) return null;
    const semi = catalogs.semiProducts.get(line.semi_product);
    if (semi === undefined) return null;
    const factor = semiFactor(line, semi);
    if (factor === null) return null;
    return { token, factor, lines: semiLines(semi), sections: [], method: semi.method };
  }
  return null;
}

function byId<T extends { id: number }>(rows: T[]): Map<number, T> {
  return new Map(rows.map((row) => [row.id, row]));
}

function expandNode(
  line: TechCardLine,
  catalogs: Catalogs,
  path: Set<string>,
  keyPrefix: string,
  chapters: ExpandedChapter[],
) {
  const opened = open(line, catalogs, path);
  if (opened === null) return;
  const next = new Set(path);
  next.add(opened.token);
  const prefix = `${keyPrefix}/${opened.token}`;
  const scaledBase = opened.lines.map((row) => scaleLine(row, opened.factor));
  for (const child of scaledBase) {
    if (open(child, catalogs, next) !== null) expandNode(child, catalogs, next, prefix, chapters);
  }
  for (const section of opened.sections) {
    const scaledSection = section.lines.map((row) => scaleLine(row, opened.factor));
    const sectionPrefix = `${prefix}-section-${section.id}`;
    for (const child of scaledSection) {
      if (open(child, catalogs, next) !== null) expandNode(child, catalogs, next, sectionPrefix, chapters);
    }
    chapters.push({
      key: sectionPrefix,
      name: `${line.name} — ${section.name}`,
      quantity: null,
      quantityUnit: null,
      lines: scaledSection,
      method: section.method,
    });
  }
  chapters.push({
    key: `${prefix}-line-${line.id}`,
    name: line.name,
    quantity: line.quantity,
    quantityUnit: line.quantity_unit,
    lines: scaledBase,
    method: opened.method,
  });
}

export function hasExpandableLines(lines: TechCardLine[], sections: { lines: TechCardLine[] }[]): boolean {
  for (const line of lines) {
    if (line.semi_product !== null || line.nested_tech_card !== null) return true;
  }
  for (const section of sections) {
    for (const line of section.lines) {
      if (line.semi_product !== null || line.nested_tech_card !== null) return true;
    }
  }
  return false;
}

export function expandRecipe(
  lines: TechCardLine[],
  sections: { lines: TechCardLine[] }[],
  techCards: TechCard[],
  semiProducts: SemiProduct[],
): ExpandedChapter[] {
  const catalogs: Catalogs = { techCards: byId(techCards), semiProducts: byId(semiProducts) };
  const path = new Set<string>();
  const chapters: ExpandedChapter[] = [];
  const visit = (rows: TechCardLine[], prefix: string) => {
    for (const line of rows) {
      if (open(line, catalogs, path) !== null) expandNode(line, catalogs, path, prefix, chapters);
    }
  };
  visit(lines, "base");
  sections.forEach((section, index) => visit(section.lines, `section-${index}`));
  return chapters;
}
