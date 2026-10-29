"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { GroupPicker } from "@/components/crm/GroupPicker";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { newDraftKey } from "@/components/menu/ComponentLinesEditor";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardTitle, Field, QueryState, formatQuantity } from "@/components/menu/ui";
import { useFinishedProductions, useTechCards } from "@/hooks/useStock";
import type { FinishedProduction, FinishedProductionBody, TechCard } from "@/lib/api/types";
import type { CrmItemModifierDraft } from "@/lib/crmItems";
import { getTbilisiTodayIsoDate } from "@/lib/format";

type LineDraft = {
  key: string;
  tech_card: string;
  weight_kg: string;
  modifiers: CrmItemModifierDraft[];
  quantity: string;
};

type FinishedDraft = { date: string; comment: string; lines: LineDraft[] };

function emptyLine(): LineDraft {
  return { key: newDraftKey(), tech_card: "", weight_kg: "", modifiers: [], quantity: "1" };
}

function draftFrom(row: FinishedProduction | null): FinishedDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), comment: "", lines: [emptyLine()] };
  }
  return {
    date: row.date,
    comment: row.comment,
    lines: row.lines.map((line) => ({
      key: newDraftKey(),
      tech_card: String(line.tech_card),
      weight_kg: line.weight_kg ?? "",
      modifiers: line.modifiers.map((modifier) => ({
        modifier: modifier.modifier,
        quantity: String(modifier.quantity),
      })),
      quantity: String(line.quantity),
    })),
  };
}

function lineBody(line: LineDraft, card: TechCard | undefined): FinishedProductionBody["lines"][number] {
  return {
    tech_card: Number(line.tech_card),
    weight_kg: card?.kind === "weighted" ? line.weight_kg.replace(",", ".") : null,
    modifiers: line.modifiers.map((modifier) => ({
      modifier: modifier.modifier,
      quantity: Number(modifier.quantity),
    })),
    quantity: Number(line.quantity),
  };
}

export function FinishedProductionsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const productions = useFinishedProductions();
  const techCards = useTechCards();
  const [editing, setEditing] = useState<FinishedProduction | null>(null);
  const [draft, setDraft] = useState<FinishedDraft | null>(null);
  const cards = techCards.list.data ?? [];

  const open = (row: FinishedProduction | null) => {
    productions.save.reset();
    productions.remove.reset();
    setEditing(row);
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  const updateLine = (key: string, patch: Partial<LineDraft>) => {
    if (draft === null) return;
    setDraft({
      ...draft,
      lines: draft.lines.map((line) => (line.key === key ? { ...line, ...patch } : line)),
    });
  };

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.finishedGoods")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <p className="mt-2 text-xs text-[var(--muted-2)]">{t("finishedProductionHint")}</p>
        <QueryState isLoading={productions.list.isLoading} isError={productions.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("date")}</th>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("createdBy")}</th>
              </tr>
            </thead>
            <tbody>
              {(productions.list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className="py-2">{row.date}</td>
                  <td className="py-2">
                    {row.lines
                      .map((line) => `${line.name} ×${line.quantity}`)
                      .join(", ")}
                  </td>
                  <td className="py-2">{row.created_by_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editing === null ? t("newFinishedProduction") : `${t("inventory.finishedGoods")} · ${editing.date}`}
          pending={productions.save.isPending}
          error={productions.save.error ?? productions.remove.error}
          submitLabel={t("save")}
          onSubmit={() => {
            const body: FinishedProductionBody = {
              date: draft.date,
              comment: draft.comment,
              lines: draft.lines.map((line) =>
                lineBody(
                  line,
                  cards.find((card) => String(card.id) === line.tech_card),
                ),
              ),
            };
            productions.save.mutate({ id: editing ? editing.id : null, body }, { onSuccess: close });
          }}
          onDelete={editing === null ? null : () => productions.remove.mutate(editing.id, { onSuccess: close })}
          deletePending={productions.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("date")}>
                <Input
                  type="date"
                  required
                  value={draft.date}
                  onChange={(event) => setDraft({ ...draft, date: event.target.value })}
                />
              </Field>
              <Field label={t("comment")}>
                <Textarea
                  value={draft.comment}
                  onChange={(event) => setDraft({ ...draft, comment: event.target.value })}
                />
              </Field>
            </div>
            {draft.lines.map((line) => {
              const card = cards.find((row) => String(row.id) === line.tech_card);
              return (
                <div key={line.key} className="grid gap-3 rounded-2xl border border-[var(--line)] p-3">
                  <div className="grid gap-3 sm:grid-cols-[1fr_8rem_6rem_auto]">
                    <Field label={t("techCard")}>
                      <SearchSelect
                        options={cards
                          .filter((row) => row.is_active || String(row.id) === line.tech_card)
                          .map((row) => ({ value: String(row.id), label: row.name }))}
                        value={line.tech_card}
                        onChange={(tech_card) => updateLine(line.key, { tech_card, modifiers: [], weight_kg: "" })}
                        placeholder={t("chooseComponent")}
                        required={true}
                        className=""
                      />
                    </Field>
                    {card?.kind === "weighted" ? (
                      <Field label={t("weightKg")}>
                        <Input
                          required
                          inputMode="decimal"
                          value={line.weight_kg}
                          onChange={(event) => updateLine(line.key, { weight_kg: event.target.value })}
                        />
                      </Field>
                    ) : (
                      <span />
                    )}
                    <Field label={t("pieces")}>
                      <Input
                        required
                        inputMode="numeric"
                        value={line.quantity}
                        onChange={(event) => updateLine(line.key, { quantity: event.target.value })}
                      />
                    </Field>
                    <div className="flex items-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={t("removeLine")}
                        onClick={() =>
                          setDraft({ ...draft, lines: draft.lines.filter((row) => row.key !== line.key) })
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {card && card.modifier_groups.length > 0 ? (
                    <div className="grid gap-3">
                      {card.modifier_groups.map((group) => (
                        <GroupPicker
                          key={group.id}
                          group={group}
                          selected={line.modifiers}
                          onChange={(modifiers) => updateLine(line.key, { modifiers })}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
            <div>
              <Button type="button" variant="outline" size="sm" onClick={() => setDraft({ ...draft, lines: [...draft.lines, emptyLine()] })}>
                <Plus className="mr-1 h-4 w-4" />
                {t("addLine")}
              </Button>
            </div>
            {editing && editing.consumed.length > 0 ? (
              <div className="grid gap-1">
                <CardTitle>{t("consumed")}</CardTitle>
                <ul className="text-sm text-[var(--ink)]">
                  {editing.consumed.map((movement) => (
                    <li key={movement.id}>
                      {movement.name}: {formatQuantity(String(-Number(movement.quantity)))} {units(movement.unit)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}
