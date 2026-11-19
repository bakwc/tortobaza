"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, QueryState } from "@/components/menu/ui";
import { WishlistShell } from "@/components/wishlist/WishlistShell";
import { useCan } from "@/hooks/useAuth";
import { useWishlist } from "@/hooks/useWishlist";
import { formatMoney } from "@/lib/format";
import type { WishlistItem, WishlistItemBody } from "@/lib/api/types";

type Draft = {
  title: string;
  purpose: string;
  priority: string;
  cost: string;
};

function nextPriority(rows: WishlistItem[]): number {
  return rows.reduce((max, row) => Math.max(max, row.priority), 0) + 1;
}

function draftFrom(row: WishlistItem | null, rows: WishlistItem[]): Draft {
  if (row === null) {
    return { title: "", purpose: "", priority: String(nextPriority(rows)), cost: "" };
  }
  return {
    title: row.title,
    purpose: row.purpose,
    priority: String(row.priority),
    cost: row.cost ?? "",
  };
}

function bodyFrom(draft: Draft): WishlistItemBody {
  const cost = draft.cost.trim();
  return {
    title: draft.title.trim(),
    purpose: draft.purpose.trim(),
    priority: Number(draft.priority),
    cost: cost === "" ? null : cost,
  };
}

export function WishlistPanel() {
  const t = useTranslations("wishlist");
  const stock = useTranslations("stock");
  const canEdit = useCan("edit_wishlist");
  const items = useWishlist();
  const rows = items.list.data ?? [];
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);

  const open = (row: WishlistItem | null) => {
    items.save.reset();
    items.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(draftFrom(row, rows));
  };

  const close = () => setDraft(null);

  return (
    <WishlistShell section="purchases">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("purchases")}</CardTitle>
          {canEdit ? (
            <Button type="button" size="sm" onClick={() => open(null)}>
              <Plus className="mr-1 h-4 w-4" />
              {t("add")}
            </Button>
          ) : null}
        </div>
        <QueryState isLoading={items.list.isLoading} isError={items.list.isError}>
          {rows.length === 0 ? (
            <p className="mt-4 text-sm text-[var(--muted-2)]">{t("empty")}</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                  <tr>
                    <th className="w-28 py-2 pr-3">{t("priority")}</th>
                    <th className="py-2 pr-3">{t("what")}</th>
                    <th className="py-2 pr-3">{t("why")}</th>
                    <th className="w-36 py-2 text-right">{t("cost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => open(row)}
                      className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                    >
                      <td className="py-3 pr-3 tabular-nums font-medium">{row.priority}</td>
                      <td className="py-3 pr-3 font-medium">{row.title}</td>
                      <td className="py-3 pr-3 whitespace-pre-wrap text-[var(--ink)]/80">{row.purpose}</td>
                      <td className="py-3 text-right tabular-nums">
                        {row.cost === null ? "—" : formatMoney(row.cost, "GEL")}
                      </td>
                    </tr>
                  ))}
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
          title={editingId === null ? t("newPurchase") : draft.title}
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
            <Field label={t("what")}>
              <Input
                required
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
              />
            </Field>
            <Field label={t("why")}>
              <Textarea
                value={draft.purpose}
                onChange={(event) => setDraft({ ...draft, purpose: event.target.value })}
              />
            </Field>
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
            <Field label={t("cost")}>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={draft.cost}
                onChange={(event) => setDraft({ ...draft, cost: event.target.value })}
              />
            </Field>
          </div>
        </EditorDialog>
      ) : null}
    </WishlistShell>
  );
}
