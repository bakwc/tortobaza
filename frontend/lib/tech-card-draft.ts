import type { ComponentLineDraft } from "@/components/menu/ComponentLinesEditor";

export type GroupLinkDraft = { group: number; is_required: boolean | null };

export type ModifierComposition = { scales_by_weight: boolean; lines: ComponentLineDraft[] };

export type SectionDraft = {
  key: string;
  id: number | null;
  name: string;
  method: string;
  lines: ComponentLineDraft[];
};

export type TechCardDraft = {
  name: string;
  category: number | null;
  kind: "weighted" | "piece";
  basis_weight_kg: string;
  basis_quantity: string;
  sale_price: string;
  method: string;
  shelf_life_days: string;
  shelf_life_hours: string;
  storage_temperature: string;
  is_active: boolean;
  lines: ComponentLineDraft[];
  sections: SectionDraft[];
  groups: GroupLinkDraft[];
  compositions: Record<number, ModifierComposition>;
};

function draftStorageKey(id: number | null): string {
  if (id === null) return "tech-card-draft:new";
  return `tech-card-draft:${id}`;
}

export function readTechCardDraft(id: number | null): TechCardDraft | null {
  const raw = window.localStorage.getItem(draftStorageKey(id));
  if (raw === null) return null;
  return JSON.parse(raw) as TechCardDraft;
}

export function writeTechCardDraft(id: number | null, draft: TechCardDraft): void {
  window.localStorage.setItem(draftStorageKey(id), JSON.stringify(draft));
}

export function clearTechCardDraft(id: number | null): void {
  window.localStorage.removeItem(draftStorageKey(id));
}

function remapComponent(component: string, sectionKeys: Map<string, string>): string {
  if (!component.startsWith("section:")) return component;
  const next = sectionKeys.get(component.slice("section:".length));
  if (next === undefined) return component;
  return `section:${next}`;
}

function normalizeLine(line: ComponentLineDraft, sectionKeys: Map<string, string>) {
  return {
    component: remapComponent(line.component, sectionKeys),
    quantity: line.quantity,
    quantity_unit: line.quantity_unit,
    loss_percent: line.loss_percent,
    unit_cost: line.unit_cost,
    suggestion: line.suggestion,
  };
}

function normalizeDraft(draft: TechCardDraft) {
  const sectionKeys = new Map<string, string>();
  draft.sections.forEach((section, index) => {
    sectionKeys.set(section.key, String(index));
  });
  const compositionIds = Object.keys(draft.compositions).sort((left, right) => Number(left) - Number(right));
  return {
    name: draft.name,
    category: draft.category,
    kind: draft.kind,
    basis_weight_kg: draft.basis_weight_kg,
    basis_quantity: draft.basis_quantity,
    sale_price: draft.sale_price,
    method: draft.method,
    shelf_life_days: draft.shelf_life_days,
    shelf_life_hours: draft.shelf_life_hours,
    storage_temperature: draft.storage_temperature,
    is_active: draft.is_active,
    lines: draft.lines.map((line) => normalizeLine(line, sectionKeys)),
    sections: draft.sections.map((section) => ({
      id: section.id,
      name: section.name,
      method: section.method,
      lines: section.lines.map((line) => normalizeLine(line, sectionKeys)),
    })),
    groups: draft.groups,
    compositions: compositionIds.map((id) => {
      const composition = draft.compositions[Number(id)];
      return {
        id: Number(id),
        scales_by_weight: composition.scales_by_weight,
        lines: composition.lines.map((line) => normalizeLine(line, sectionKeys)),
      };
    }),
  };
}

export function techCardDraftsEqual(left: TechCardDraft, right: TechCardDraft): boolean {
  return JSON.stringify(normalizeDraft(left)) === JSON.stringify(normalizeDraft(right));
}
