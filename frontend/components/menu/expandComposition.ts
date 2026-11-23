import type { MenuUnit, SemiProduct, TechCard } from "@/lib/api/types";

export type TechCardLine = TechCard["lines"][number];

export type ExpandedChapter = {
  key: string;
  name: string;
  quantity: string | null;
  quantityUnit: MenuUnit | null;
  lines: TechCardLine[];
};

export type ExpandedRecipe = {
  lines: TechCardLine[];
  chapters: ExpandedChapter[];
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

type Split = {
  leaves: TechCardLine[];
  nested: TechCardLine[];
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

function split(lines: TechCardLine[], factor: number, catalogs: Catalogs, path: Set<string>): Split {
  const leaves: TechCardLine[] = [];
  const nested: TechCardLine[] = [];
  for (const raw of lines) {
    const line = scaleLine(raw, factor);
    if (open(line, catalogs, path) === null) leaves.push(line);
    else nested.push(line);
  }
  return { leaves, nested };
}

function pushMethod(methods: string[], name: string, method: string) {
  const trimmed = method.trim();
  if (!trimmed) return;
  methods.push(`## ${name}\n${trimmed}`);
}

function expandNode(
  line: TechCardLine,
  catalogs: Catalogs,
  path: Set<string>,
  keyPrefix: string,
  chapters: ExpandedChapter[],
  methods: string[],
) {
  const opened = open(line, catalogs, path);
  if (opened === null) return;
  const next = new Set(path);
  next.add(opened.token);
  const prefix = `${keyPrefix}/${opened.token}`;
  const parts = split(opened.lines, opened.factor, catalogs, next);
  chapters.push({
    key: `${prefix}-line-${line.id}`,
    name: line.name,
    quantity: line.quantity,
    quantityUnit: line.quantity_unit,
    lines: parts.leaves,
  });
  pushMethod(methods, line.name, opened.method);
  for (const child of parts.nested) expandNode(child, catalogs, next, prefix, chapters, methods);
  for (const section of opened.sections) {
    const sectionParts = split(section.lines, opened.factor, catalogs, next);
    const sectionName = `${line.name} — ${section.name}`;
    const sectionPrefix = `${prefix}-section-${section.id}`;
    chapters.push({
      key: sectionPrefix,
      name: sectionName,
      quantity: null,
      quantityUnit: null,
      lines: sectionParts.leaves,
    });
    pushMethod(methods, sectionName, section.method);
    for (const child of sectionParts.nested) expandNode(child, catalogs, next, sectionPrefix, chapters, methods);
  }
}

function byId<T extends { id: number }>(rows: T[]): Map<number, T> {
  return new Map(rows.map((row) => [row.id, row]));
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
  sections: { name: string; method: string; lines: TechCardLine[] }[],
  rootMethod: string,
  techCards: TechCard[],
  semiProducts: SemiProduct[],
): ExpandedRecipe {
  const catalogs: Catalogs = { techCards: byId(techCards), semiProducts: byId(semiProducts) };
  const path = new Set<string>();
  const chapters: ExpandedChapter[] = [];
  const methods: string[] = [];
  const base = split(lines, 1, catalogs, path);
  for (const child of base.nested) expandNode(child, catalogs, path, "base", chapters, methods);
  sections.forEach((section, index) => {
    const parts = split(section.lines, 1, catalogs, path);
    const prefix = `section-${index}`;
    chapters.push({
      key: prefix,
      name: section.name,
      quantity: null,
      quantityUnit: null,
      lines: parts.leaves,
    });
    pushMethod(methods, section.name, section.method);
    for (const child of parts.nested) expandNode(child, catalogs, path, prefix, chapters, methods);
  });
  const own = rootMethod.trim();
  if (own) methods.push(own);
  return { lines: base.leaves, chapters, method: methods.join("\n\n") };
}
