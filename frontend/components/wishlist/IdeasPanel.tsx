"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, NativeSelect, QueryState } from "@/components/menu/ui";
import { WishlistShell } from "@/components/wishlist/WishlistShell";
import { useCan } from "@/hooks/useAuth";
import { useIdeas } from "@/hooks/useIdeas";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Idea, IdeaBody, IdeaStatus } from "@/lib/api/types";

const IDEA_STATUSES = ["doing", "planned", "unknown", "rejected", "succeeded", "failed"] as const;

const STATUS_LABEL = {
  doing: "statusDoing",
  planned: "statusPlanned",
  unknown: "statusUnknown",
  rejected: "statusRejected",
  succeeded: "statusSucceeded",
  failed: "statusFailed",
} as const;

type StatusFilter = "all" | IdeaStatus;

type Draft = {
  problem: string;
  description: string;
  priority: string;
  cost: string;
  days: string;
  hours: string;
  status: IdeaStatus;
};

function nextPriority(rows: Idea[]): number {
  return rows.reduce((max, row) => Math.max(max, row.priority), 0) + 1;
}

function durationParts(seconds: number | null): { days: string; hours: string } {
  if (seconds === null) return { days: "", hours: "" };
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return { days: String(days), hours: String(hours) };
}

function durationSeconds(days: string, hours: string): number | null {
  const daysText = days.trim();
  const hoursText = hours.trim();
  if (daysText === "" && hoursText === "") return null;
  const dayCount = daysText === "" ? 0 : Number(daysText);
  const hourCount = hoursText === "" ? 0 : Number(hoursText);
  return dayCount * 86400 + hourCount * 3600;
}

function draftFrom(row: Idea | null, rows: Idea[]): Draft {
  if (row === null) {
    return {
      problem: "",
      description: "",
      priority: String(nextPriority(rows)),
      cost: "",
      days: "",
      hours: "",
      status: "unknown",
    };
  }
  const duration = durationParts(row.duration_seconds);
  return {
    problem: row.problem,
    description: row.description,
    priority: String(row.priority),
    cost: row.cost ?? "",
    days: duration.days,
    hours: duration.hours,
    status: row.status,
  };
}

function bodyFrom(draft: Draft): IdeaBody {
  const cost = draft.cost.trim();
  return {
    problem: draft.problem.trim(),
    description: draft.description.trim(),
    priority: Number(draft.priority),
    cost: cost === "" ? null : cost,
    duration_seconds: durationSeconds(draft.days, draft.hours),
    status: draft.status,
  };
}

export function IdeasPanel() {
  const t = useTranslations("wishlist");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_wishlist");
  const items = useIdeas();
  const rows = items.list.data ?? [];
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const visible = filter === "all" ? rows : rows.filter((row) => row.status === filter);

  const open = (row: Idea | null) => {
    items.save.reset();
    items.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(draftFrom(row, rows));
  };

  const close = () => setDraft(null);

  const chips = [
    { key: "all" as const, label: t("allStatuses"), count: rows.length },
    ...IDEA_STATUSES.map((status) => ({
      key: status,
      label: t(STATUS_LABEL[status]),
      count: rows.filter((row) => row.status === status).length,
    })),
  ];

  return (
    <WishlistShell section="ideas">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("ideas")}</CardTitle>
          {canEdit ? (
            <Button type="button" size="sm" onClick={() => open(null)}>
              <Plus className="mr-1 h-4 w-4" />
              {t("add")}
            </Button>
          ) : null}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              onClick={() => setFilter(chip.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                filter === chip.key
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
              )}
            >
              {chip.label}
              <span
                className={cn(
                  "rounded-full px-1.5 text-[11px]",
                  filter === chip.key ? "bg-white/25" : "bg-[var(--cream)]",
                )}
              >
                {chip.count}
              </span>
            </button>
          ))}
        </div>
        <QueryState isLoading={items.list.isLoading} isError={items.list.isError}>
          {visible.length === 0 ? (
            <p className="mt-4 text-sm text-[var(--muted-2)]">{t("empty")}</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[880px] text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="w-28 py-2 pr-3">{t("priority")}</th>
                    <th className="py-2 pr-3">{t("problem")}</th>
                    <th className="py-2 pr-3">{t("description")}</th>
                    <th className="w-36 py-2 pr-3 text-right">{t("investment")}</th>
                    <th className="w-32 py-2 pr-3">{t("duration")}</th>
                    <th className="w-48 py-2">{t("status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((row) => {
                    const duration = durationParts(row.duration_seconds);
                    return (
                      <tr
                        key={row.id}
                        onClick={() => open(row)}
                        className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                      >
                        <td className="py-3 pr-3 tabular-nums font-medium">{row.priority}</td>
                        <td className="py-3 pr-3 whitespace-pre-wrap text-[var(--ink)]/80">{row.problem}</td>
                        <td className="py-3 pr-3 whitespace-pre-wrap font-medium">{row.description}</td>
                        <td className="py-3 pr-3 text-right tabular-nums">
                          {row.cost === null ? "—" : formatMoney(row.cost, "GEL")}
                        </td>
                        <td className="py-3 pr-3 tabular-nums">
                          {row.duration_seconds === null
                            ? "—"
                            : t("durationValue", { days: Number(duration.days), hours: Number(duration.hours) })}
                        </td>
                        <td className="py-3">{t(STATUS_LABEL[row.status])}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </QueryState>
      </Card>
      {draft !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newIdea") : draft.description}
          pending={items.save.isPending}
          error={items.save.error ?? items.remove.error}
          submitLabel={canEdit ? stock("save") : null}
          onSubmit={() =>
            items.save.mutate({ id: editingId, body: bodyFrom(draft) }, { onSuccess: close })
          }
          onDelete={
            canEdit && editingId !== null
              ? () => items.remove.mutate(editingId, { onSuccess: close })
              : null
          }
          deletePending={items.remove.isPending}
          headerAction={null}
          below={null}
        >
          <div className="grid gap-4">
            <Field label={t("priority")}>
              <Input
                required
                type="number"
                min={0}
                step={1}
                value={draft.priority}
                onChange={(event) => setDraft({ ...draft, priority: event.target.value })}
              />
            </Field>
            <Field label={t("problem")}>
              <Textarea
                value={draft.problem}
                onChange={(event) => setDraft({ ...draft, problem: event.target.value })}
              />
            </Field>
            <Field label={t("description")}>
              <Textarea
                required
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
              />
            </Field>
            <Field label={t("investment")}>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={draft.cost}
                onChange={(event) => setDraft({ ...draft, cost: event.target.value })}
              />
            </Field>
            <div className="grid gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">{t("duration")}</span>
              <div className="grid grid-cols-2 gap-4">
                <Field label={t("days")}>
                  <Input
                    type="number"
                    min={0}
                    step={1}
                    value={draft.days}
                    onChange={(event) => setDraft({ ...draft, days: event.target.value })}
                  />
                </Field>
                <Field label={t("hours")}>
                  <Input
                    type="number"
                    min={0}
                    step={1}
                    value={draft.hours}
                    onChange={(event) => setDraft({ ...draft, hours: event.target.value })}
                  />
                </Field>
              </div>
            </div>
            <Field label={t("status")}>
              <NativeSelect
                required
                value={draft.status}
                onChange={(event) => setDraft({ ...draft, status: event.target.value as IdeaStatus })}
              >
                {IDEA_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {t(STATUS_LABEL[status])}
                  </option>
                ))}
              </NativeSelect>
            </Field>
          </div>
        </EditorDialog>
      ) : null}
    </WishlistShell>
  );
}
