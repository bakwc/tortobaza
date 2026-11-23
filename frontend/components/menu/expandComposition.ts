import type { MenuUnit, SemiProduct, TechCard } from "@/lib/api/types";

export type TechCardLine = TechCard["lines"][number];

export type LineBlock = {
  kind: "lines";
  key: string;
  lines: TechCardLine[];
};

export type ChapterBlock = {
  kind: "chapter";
  key: string;
  title: string;
  quantity: string | null;
  quantityUnit: MenuUnit | null;
  method: string;
  depth: number;
  blocks: CompositionBlock[];
};

export type CompositionBlock = LineBlock | ChapterBlock;

export type PrintRow = {
  key: string;
  name: string | null;
  quantity: string | null;
  quantityUnit: MenuUnit | null;
  depth: number;
  lines: TechCardLine[];
  method: string;
};

type Header = {
  name: string | null;
  method: string;
  quantity: string | null;
  quantityUnit: MenuUnit | null;
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

function expandLines(
  lines: TechCardLine[],
  factor: number,
  techCards: Map<number, TechCard>,
  semiProducts: Map<number, SemiProduct>,
  path: Set<string>,
  depth: number,
  keyPrefix: string,
): CompositionBlock[] {
  const blocks: CompositionBlock[] = [];
  let bucket: TechCardLine[] = [];
  const flush = () => {
    if (bucket.length === 0) return;
    blocks.push({ kind: "lines", key: `${keyPrefix}-lines-${bucket[0].id}`, lines: bucket });
    bucket = [];
  };
  for (const raw of lines) {
    const line = scaleLine(raw, factor);
    const chapter = chapterFor(line, techCards, semiProducts, path, depth, keyPrefix);
    if (chapter === null) {
      bucket.push(line);
      continue;
    }
    flush();
    blocks.push(chapter);
  }
  flush();
  return blocks;
}

function chapterFor(
  line: TechCardLine,
  techCards: Map<number, TechCard>,
  semiProducts: Map<number, SemiProduct>,
  path: Set<string>,
  depth: number,
  keyPrefix: string,
): ChapterBlock | null {
  if (line.nested_tech_card !== null) {
    const token = `tech:${line.nested_tech_card}`;
    if (path.has(token)) return null;
    const card = techCards.get(line.nested_tech_card);
    if (card === undefined) return null;
    const factor = techCardFactor(line, card);
    if (factor === null) return null;
    const next = new Set(path);
    next.add(token);
    const prefix = `${keyPrefix}/${token}`;
    return {
      kind: "chapter",
      key: `${keyPrefix}-line-${line.id}`,
      title: line.name,
      quantity: line.quantity,
      quantityUnit: line.quantity_unit,
      method: card.method,
      depth,
      blocks: [
        ...expandLines(card.lines, factor, techCards, semiProducts, next, depth + 1, prefix),
        ...card.sections.map((section) => ({
          kind: "chapter" as const,
          key: `${prefix}-section-${section.id}`,
          title: section.name,
          quantity: null,
          quantityUnit: null,
          method: section.method,
          depth: depth + 1,
          blocks: expandLines(
            section.lines,
            factor,
            techCards,
            semiProducts,
            next,
            depth + 2,
            `${prefix}/section-${section.id}`,
          ),
        })),
      ],
    };
  }
  if (line.semi_product !== null) {
    const token = `semi:${line.semi_product}`;
    if (path.has(token)) return null;
    const semi = semiProducts.get(line.semi_product);
    if (semi === undefined) return null;
    const factor = semiFactor(line, semi);
    if (factor === null) return null;
    const next = new Set(path);
    next.add(token);
    return {
      kind: "chapter",
      key: `${keyPrefix}-line-${line.id}`,
      title: line.name,
      quantity: line.quantity,
      quantityUnit: line.quantity_unit,
      method: semi.method,
      depth,
      blocks: expandLines(semiLines(semi), factor, techCards, semiProducts, next, depth + 1, `${keyPrefix}/${token}`),
    };
  }
  return null;
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

export function expandComposition(
  lines: TechCardLine[],
  techCards: TechCard[],
  semiProducts: SemiProduct[],
  depth: number,
): CompositionBlock[] {
  return expandLines(lines, 1, byId(techCards), byId(semiProducts), new Set(), depth, `d${depth}`);
}

function headerVisible(header: Header): boolean {
  return header.name !== null || header.method !== "";
}

function printRows(
  name: string | null,
  method: string,
  quantity: string | null,
  quantityUnit: MenuUnit | null,
  blocks: CompositionBlock[],
  depth: number,
  keyPrefix: string,
): PrintRow[] {
  const rows: PrintRow[] = [];
  let header: Header | null = { name, method, quantity, quantityUnit };
  let lines: TechCardLine[] = [];
  let lineKey = "";
  const takeHeader = (): Header => {
    const current = header ?? { name: null, method: "", quantity: null, quantityUnit: null };
    header = null;
    return current;
  };
  const flushLines = () => {
    if (lines.length === 0) return;
    const head = takeHeader();
    rows.push({
      key: lineKey,
      name: head.name,
      quantity: head.quantity,
      quantityUnit: head.quantityUnit,
      depth,
      lines,
      method: head.method,
    });
    lines = [];
  };
  for (const block of blocks) {
    if (block.kind === "lines") {
      if (lines.length === 0) lineKey = `${keyPrefix}-${block.key}`;
      lines.push(...block.lines);
      continue;
    }
    flushLines();
    if (header !== null && headerVisible(header)) {
      const head = takeHeader();
      rows.push({
        key: `${keyPrefix}-head-${rows.length}`,
        name: head.name,
        quantity: head.quantity,
        quantityUnit: head.quantityUnit,
        depth,
        lines: [],
        method: head.method,
      });
    }
    rows.push(
      ...printRows(
        block.title,
        block.method,
        block.quantity,
        block.quantityUnit,
        block.blocks,
        block.depth,
        `${keyPrefix}-${block.key}`,
      ),
    );
  }
  flushLines();
  if (header !== null && headerVisible(header)) {
    const head = takeHeader();
    rows.push({
      key: `${keyPrefix}-tail`,
      name: head.name,
      quantity: head.quantity,
      quantityUnit: head.quantityUnit,
      depth,
      lines: [],
      method: head.method,
    });
  }
  return rows;
}

export function compositionPrintRows(
  name: string | null,
  method: string,
  blocks: CompositionBlock[],
  keyPrefix: string,
): PrintRow[] {
  return printRows(name, method, null, null, blocks, 0, keyPrefix);
}
