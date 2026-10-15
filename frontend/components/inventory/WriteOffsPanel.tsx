"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ComponentLinesEditor,
  componentOptions,
  draftFromLine,
  linesToQuantityBody,
  type ComponentLineDraft,
} from "@/components/menu/ComponentLinesEditor";
import { EditorDialog } from "@/components/menu/EditorDialog";
import {
  Card,
  CardTitle,
  ErrorText,
  Field,
  NativeSelect,
  QueryState,
  formatMoney,
  formatQuantity,
} from "@/components/menu/ui";
import { useIngredients, useSemiProducts, useWriteOffReasons, useWriteOffs } from "@/hooks/useStock";
import type { WriteOff } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";

type WriteOffDraft = { date: string; reason: string; comment: string; lines: ComponentLineDraft[] };

function draftFrom(row: WriteOff | null): WriteOffDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), reason: "", comment: "", lines: [] };
  }
  return { date: row.date, reason: String(row.reason), comment: row.comment, lines: row.lines.map(draftFromLine) };
}

export function WriteOffsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const writeOffs = useWriteOffs();
  const reasons = useWriteOffReasons();
  const ingredients = useIngredients();
  const semiProducts = useSemiProducts();
  const [editing, setEditing] = useState<WriteOff | null>(null);
  const [draft, setDraft] = useState<WriteOffDraft | null>(null);
  const [newReason, setNewReason] = useState("");

  const options = componentOptions(
    ingredients.list.data ?? [],
    semiProducts.list.data ?? [],
    "all",
    t("ingredient"),
    t("semiProduct"),
  );

  const open = (row: WriteOff | null) => {
    writeOffs.save.reset();
    writeOffs.remove.reset();
    setEditing(row);
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.writeOffs")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={writeOffs.list.isLoading} isError={writeOffs.list.isError}>
          <div className="mt-4 grid gap-2">
            {(writeOffs.list.data ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => open(row)}
                className="rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-[var(--ink)]">
                    {row.date} · {row.reason_name}
                  </span>
                  {row.total_cost !== undefined ? (
                    <span className="text-sm font-semibold">{formatMoney(row.total_cost)}</span>
                  ) : null}
                </div>
                <p className="mt-1 text-sm text-[var(--muted-2)]">
                  {row.lines.map((line) => `${line.name} ${formatQuantity(line.quantity)} ${units(line.unit)}`).join(", ")}
                </p>
              </button>
            ))}
          </div>
        </QueryState>
      </Card>

      <Card>
        <CardTitle>{t("writeOffReasons")}</CardTitle>
        <div className="mt-4 flex flex-wrap gap-2">
          {(reasons.list.data ?? []).map((row) => (
            <span
              key={row.id}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] px-3 py-1 text-sm"
            >
              {row.name}
              <button
                type="button"
                aria-label={t("delete")}
                onClick={() => reasons.remove.mutate(row.id)}
                className="text-[var(--muted-2)] hover:text-[var(--danger)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </span>
          ))}
        </div>
        <form
          className="mt-4 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            reasons.save.mutate({ id: null, body: { name: newReason } }, { onSuccess: () => setNewReason("") });
          }}
        >
          <Input
            required
            value={newReason}
            placeholder={t("newReason")}
            onChange={(event) => setNewReason(event.target.value)}
          />
          <Button type="submit" disabled={reasons.save.isPending}>
            {t("add")}
          </Button>
        </form>
        <div className="mt-2">
          <ErrorText error={reasons.save.error ?? reasons.remove.error} />
        </div>
      </Card>

      {draft ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          title={editing === null ? t("newWriteOff") : `${editing.reason_name} · ${editing.date}`}
          pending={writeOffs.save.isPending}
          error={writeOffs.save.error ?? writeOffs.remove.error}
          submitLabel={t("save")}
          onSubmit={() =>
            writeOffs.save.mutate(
              {
                id: editing ? editing.id : null,
                body: {
                  date: draft.date,
                  reason: Number(draft.reason),
                  comment: draft.comment,
                  lines: linesToQuantityBody(draft.lines),
                },
              },
              { onSuccess: close },
            )
          }
          onDelete={editing === null ? null : () => writeOffs.remove.mutate(editing.id, { onSuccess: close })}
          deletePending={writeOffs.remove.isPending}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("date")}>
              <Input
                type="date"
                required
                value={draft.date}
                onChange={(event) => setDraft({ ...draft, date: event.target.value })}
              />
            </Field>
            <Field label={t("reason")}>
              <NativeSelect
                required
                value={draft.reason}
                onChange={(event) => setDraft({ ...draft, reason: event.target.value })}
              >
                <option value="">{t("chooseReason")}</option>
                {(reasons.list.data ?? []).map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label={t("comment")} className="sm:col-span-2">
              <Textarea value={draft.comment} onChange={(event) => setDraft({ ...draft, comment: event.target.value })} />
            </Field>
          </div>
          <CardTitle>{t("lines")}</CardTitle>
          <ComponentLinesEditor
            lines={draft.lines}
            onChange={(lines) => setDraft({ ...draft, lines })}
            options={options}
            extraColumn={null}
            quantityLabel={t("quantity")}
          />
        </EditorDialog>
      ) : null}
    </div>
  );
}
