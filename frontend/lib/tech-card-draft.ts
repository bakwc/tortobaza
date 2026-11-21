import type { ComponentLineDraft } from "@/components/menu/ComponentLinesEditor";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api/client";
import { TechCardDraftRecordSchema, type TechCardDraftRecord } from "@/lib/api/types";

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

const DRAFT_INDEX_KEY = "tech-card-draft:v2:index";
const DRAFT_DELETE_KEY = "tech-card-draft:v2:deleting";

export type StoredTechCardDraft = {
  clientId: string;
  techCardId: number | null;
  clientUpdatedAt: string;
  pending: boolean;
  rejectedAt: string | null;
  draft: TechCardDraft;
};

function draftStorageKey(clientId: string): string {
  return `tech-card-draft:v2:${clientId}`;
}

function readIndex(): string[] {
  const raw = window.localStorage.getItem(DRAFT_INDEX_KEY);
  if (raw === null) return [];
  return JSON.parse(raw) as string[];
}

function writeIndex(ids: string[]): void {
  window.localStorage.setItem(DRAFT_INDEX_KEY, JSON.stringify(ids));
}

function readDeleting(): string[] {
  const raw = window.localStorage.getItem(DRAFT_DELETE_KEY);
  if (raw === null) return [];
  return JSON.parse(raw) as string[];
}

function writeDeleting(ids: string[]): void {
  window.localStorage.setItem(DRAFT_DELETE_KEY, JSON.stringify(ids));
}

export function readStoredTechCardDraft(clientId: string): StoredTechCardDraft | null {
  const raw = window.localStorage.getItem(draftStorageKey(clientId));
  if (raw === null) return null;
  return JSON.parse(raw) as StoredTechCardDraft;
}

export function listStoredTechCardDrafts(): StoredTechCardDraft[] {
  const ids = readIndex();
  const rows: StoredTechCardDraft[] = [];
  const kept: string[] = [];
  for (const clientId of ids) {
    const row = readStoredTechCardDraft(clientId);
    if (row === null) continue;
    rows.push(row);
    kept.push(clientId);
  }
  if (kept.length !== ids.length) writeIndex(kept);
  return rows;
}

export function findStoredTechCardDraftByCard(techCardId: number): StoredTechCardDraft | null {
  return listStoredTechCardDrafts().find((row) => row.techCardId === techCardId) ?? null;
}

export function writeStoredTechCardDraft(row: StoredTechCardDraft): void {
  window.localStorage.setItem(draftStorageKey(row.clientId), JSON.stringify(row));
  const ids = readIndex();
  if (!ids.includes(row.clientId)) writeIndex([...ids, row.clientId]);
}

export function clearStoredTechCardDraft(clientId: string): void {
  window.localStorage.removeItem(draftStorageKey(clientId));
  writeIndex(readIndex().filter((id) => id !== clientId));
}

function adoptServerDraft(record: TechCardDraftRecord): void {
  const local =
    record.tech_card !== null
      ? findStoredTechCardDraftByCard(record.tech_card)
      : readStoredTechCardDraft(record.client_id);
  if (local !== null && local.clientId !== record.client_id) clearStoredTechCardDraft(local.clientId);
  writeStoredTechCardDraft({
    clientId: record.client_id,
    techCardId: record.tech_card,
    clientUpdatedAt: record.client_updated_at,
    pending: false,
    rejectedAt: null,
    draft: record.payload as TechCardDraft,
  });
}

export async function pushStoredTechCardDraft(row: StoredTechCardDraft, open: boolean): Promise<"saved" | "offline" | "conflict"> {
  try {
    await api.saveTechCardDraft({
      client_id: row.clientId,
      tech_card: row.techCardId,
      client_updated_at: row.clientUpdatedAt,
      payload: row.draft,
    });
    if (readDeleting().includes(row.clientId)) {
      await api.deleteTechCardDraft(row.clientId);
      return "saved";
    }
  } catch (error) {
    if (error instanceof TypeError) return "offline";
    if (!(error instanceof ApiError) || error.status !== 409) throw error;
    const winner = TechCardDraftRecordSchema.parse(error.parsed());
    if (open) {
      const current = readStoredTechCardDraft(row.clientId);
      if (current !== null && current.clientUpdatedAt === row.clientUpdatedAt) {
        writeStoredTechCardDraft({ ...current, rejectedAt: row.clientUpdatedAt });
      }
      return "conflict";
    }
    adoptServerDraft(winner);
    return "conflict";
  }
  const current = readStoredTechCardDraft(row.clientId);
  if (current !== null && current.clientUpdatedAt === row.clientUpdatedAt) {
    writeStoredTechCardDraft({ ...current, pending: false, rejectedAt: null });
  }
  return "saved";
}

export async function flushDeletedTechCardDrafts(): Promise<void> {
  for (const clientId of readDeleting()) {
    try {
      await api.deleteTechCardDraft(clientId);
    } catch (error) {
      if (error instanceof TypeError) return;
      throw error;
    }
    writeDeleting(readDeleting().filter((id) => id !== clientId));
  }
}

export async function flushPendingTechCardDrafts(openClientId: string | null): Promise<void> {
  await flushDeletedTechCardDrafts();
  for (const row of listStoredTechCardDrafts()) {
    if (!row.pending || row.rejectedAt === row.clientUpdatedAt) continue;
    await pushStoredTechCardDraft(row, openClientId === row.clientId);
  }
}

export function mergeServerTechCardDrafts(
  records: TechCardDraftRecord[],
  openClientId: string | null,
  openTechCardId: number | null,
): void {
  const openIds = new Set<string>();
  if (openClientId !== null) openIds.add(openClientId);
  if (openTechCardId !== null) {
    const openCard = findStoredTechCardDraftByCard(openTechCardId);
    if (openCard !== null) openIds.add(openCard.clientId);
  }
  const deleting = new Set(readDeleting());
  for (const record of records) {
    if (deleting.has(record.client_id)) continue;
    const local =
      record.tech_card !== null
        ? findStoredTechCardDraftByCard(record.tech_card)
        : readStoredTechCardDraft(record.client_id);
    if (local !== null && openIds.has(local.clientId)) continue;
    if (local === null && openIds.has(record.client_id)) continue;
    const serverTime = Date.parse(record.client_updated_at);
    if (local !== null && Date.parse(local.clientUpdatedAt) >= serverTime) continue;
    adoptServerDraft(record);
  }
  const serverKeys = new Set(
    records.map((record) => (record.tech_card !== null ? `card:${record.tech_card}` : record.client_id)),
  );
  for (const local of listStoredTechCardDrafts()) {
    const key = local.techCardId !== null ? `card:${local.techCardId}` : local.clientId;
    if (serverKeys.has(key) || local.pending || openIds.has(local.clientId)) continue;
    clearStoredTechCardDraft(local.clientId);
  }
}

export async function deleteStoredTechCardDraft(clientId: string): Promise<void> {
  clearStoredTechCardDraft(clientId);
  const deleting = readDeleting();
  if (!deleting.includes(clientId)) writeDeleting([...deleting, clientId]);
  await flushDeletedTechCardDrafts();
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
    loss_quantity: line.loss_quantity,
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
