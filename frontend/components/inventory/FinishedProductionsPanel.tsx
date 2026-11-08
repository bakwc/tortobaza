"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Search, Trash2 } from "lucide-react";
import { GroupPicker } from "@/components/crm/GroupPicker";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { newDraftKey } from "@/components/menu/ComponentLinesEditor";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardTitle, Field, QueryState, formatQuantity } from "@/components/menu/ui";
import { useCan, useCurrentUser } from "@/hooks/useAuth";
import { useFinishedProductions, useProducers, useTechCardCategories, useTechCards } from "@/hooks/useStock";
import type { FinishedProduction, FinishedProductionBody, TechCard } from "@/lib/api/types";
import type { CrmItemModifierDraft } from "@/lib/crmItems";
import { getTbilisiTodayIsoDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type LineDraft = {
  key: string;
  tech_card: string;
  weight_kg: string;
  modifiers: CrmItemModifierDraft[];
  quantity: string;
};

type FinishedDraft = { date: string; comment: string; created_by: string; lines: LineDraft[] };

function emptyLine(): LineDraft {
  return { key: newDraftKey(), tech_card: "", weight_kg: "", modifiers: [], quantity: "1" };
}

function draftFrom(row: FinishedProduction | null, selfId: number): FinishedDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), comment: "", created_by: String(selfId), lines: [emptyLine()] };
  }
  return {
    date: row.date,
    comment: row.comment,
    created_by: row.created_by === null ? "" : String(row.created_by),
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
  const tForms = useTranslations("forms");
  const canEditAll = useCan("edit_finished");
  const canEditOwn = useCan("edit_own_finished");
  const canCreate = canEditAll || canEditOwn;
  const units = useTranslations("stock.units");
  const currentUser = useCurrentUser();
  const isStaff = currentUser.data?.is_staff === true;
  const productions = useFinishedProductions();
  const producers = useProducers(isStaff);
  const techCards = useTechCards();
  const categories = useTechCardCategories();
  const [editing, setEditing] = useState<FinishedProduction | null>(null);
  const [draft, setDraft] = useState<FinishedDraft | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const cards = techCards.list.data ?? [];
  const categoryByCard = new Map(cards.map((card) => [card.id, card.category]));
  const rows = productions.list.data ?? [];
  const query = search.trim().toLowerCase();
  const categoryKey = (techCardId: number): string | null => {
    const category = categoryByCard.get(techCardId);
    if (category === undefined) {
      if (techCards.list.isLoading) return null;
      return "none";
    }
    if (category === null) return "none";
    return String(category);
  };
  const matchesCategory = (row: FinishedProduction, key: string) =>
    row.lines.some((line) => categoryKey(line.tech_card) === key);
  const allGroups = [
    ...(categories.list.data ?? []).map((category) => ({
      key: String(category.id),
      label: category.name,
      count: rows.filter((row) => matchesCategory(row, String(category.id))).length,
    })),
    {
      key: "none",
      label: t("noCategory"),
      count: rows.filter((row) => matchesCategory(row, "none")).length,
    },
  ].filter((group) => group.count > 0);
  const visible = rows.filter((row) => {
    const categoryOk = categoryFilter === "all" || matchesCategory(row, categoryFilter);
    const nameOk = query === "" || row.lines.some((line) => line.name.toLowerCase().includes(query));
    return categoryOk && nameOk;
  });
  const userId = currentUser.data?.id;
  const canChange = (row: FinishedProduction | null) => {
    if (canEditAll) return true;
    if (!canEditOwn) return false;
    if (row === null) return true;
    return row.created_by_id === userId;
  };

  const open = (row: FinishedProduction | null) => {
    const user = currentUser.data;
    if (user === undefined) {
      throw new Error("Current user is not loaded.");
    }
    productions.save.reset();
    productions.remove.reset();
    setEditing(row);
    setDraft(draftFrom(row, user.id));
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
          {canCreate ? (
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
          ) : null}
        </div>
        <p className="mt-2 text-xs text-[var(--muted-2)]">{t("finishedProductionHint")}</p>
        <div className="relative mt-5">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-2)]" />
          <Input
            value={search}
            placeholder={t("searchTechCards")}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-11"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {[{ key: "all", label: t("allCategories"), count: rows.length }, ...allGroups].map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={() => setCategoryFilter(chip.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                categoryFilter === chip.key
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {chip.label}
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px]",
                  categoryFilter === chip.key ? "bg-white/25" : "bg-[var(--cream)]",
                )}
              >
                {chip.count}
              </span>
            </button>
          ))}
        </div>
        <QueryState isLoading={productions.list.isLoading} isError={productions.list.isError}>
          {visible.length === 0 ? (
            <p className="mt-4 py-6 text-center text-sm text-[var(--muted-2)]">{t("nothingFound")}</p>
          ) : (
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("date")}</th>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("pieces")}</th>
                <th className="py-2">{t("createdBy")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className="py-2">{row.date}</td>
                  <td className="py-2">
                    {row.lines.map((line) => (
                      <div key={line.id}>{line.name}</div>
                    ))}
                  </td>
                  <td className="py-2">
                    {row.lines.map((line) => (
                      <div key={line.id}>{line.quantity}</div>
                    ))}
                  </td>
                  <td className="py-2">{row.created_by_name ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          )}
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
          submitLabel={canChange(editing) ? t("save") : null}
          onSubmit={() => {
            const user = currentUser.data;
            if (user === undefined) {
              throw new Error("Current user is not loaded.");
            }
            const created_by = isStaff ? Number(draft.created_by) : editing === null ? user.id : editing.created_by;
            const body: FinishedProductionBody = {
              date: draft.date,
              comment: draft.comment,
              created_by,
              lines: draft.lines.map((line) =>
                lineBody(
                  line,
                  cards.find((card) => String(card.id) === line.tech_card),
                ),
              ),
            };
            productions.save.mutate({ id: editing ? editing.id : null, body }, { onSuccess: close });
          }}
          onDelete={canChange(editing) && editing !== null ? () => productions.remove.mutate(editing.id, { onSuccess: close }) : null}
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
              {isStaff ? (
                <Field label={t("createdBy")}>
                  <SearchSelect
                    options={(producers.data ?? []).map((person) => ({
                      value: String(person.id),
                      label: person.name,
                    }))}
                    value={draft.created_by}
                    onChange={(created_by) => setDraft({ ...draft, created_by })}
                    placeholder={t("createdBy")}
                    required={true}
                    name="created_by"
                    className=""
                  />
                </Field>
              ) : null}
              <Field label={t("comment")}>
                <Textarea
                  value={draft.comment}
                  onChange={(event) => setDraft({ ...draft, comment: event.target.value })}
                />
              </Field>
            </div>
            {draft.lines.map((line, index) => {
              const card = cards.find((row) => String(row.id) === line.tech_card);
              return (
                <div
                  key={line.key}
                  data-field-group={tForms("rowNumber", { number: index + 1 })}
                  data-error-list="lines"
                  className="grid gap-3 rounded-2xl border border-[var(--line)] p-3"
                >
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
                        name="tech_card"
                        className=""
                      />
                    </Field>
                    {card?.kind === "weighted" ? (
                      <Field label={t("weightKg")}>
                        <Input
                          name="weight_kg"
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
                        name="quantity"
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
                          key={group.group}
                          group={group}
                          selected={line.modifiers}
                          modifierPrice={() => null}
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
