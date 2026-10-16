"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FinanceAuthGate } from "@/components/finance/FinanceAuthGate";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { Card, CardTitle, Field, QueryState } from "@/components/menu/ui";
import { useSuppliers } from "@/hooks/useStock";
import type { Supplier, SupplierBody } from "@/lib/api/types";

function SuppliersList() {
  const t = useTranslations("stock");
  const suppliers = useSuppliers();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<SupplierBody | null>(null);

  const open = (row: Supplier | null) => {
    suppliers.save.reset();
    suppliers.remove.reset();
    setEditingId(row ? row.id : null);
    setDraft(row ? { name: row.name, phone: row.phone, comment: row.comment } : { name: "", phone: "", comment: "" });
  };

  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.suppliers")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={suppliers.list.isLoading} isError={suppliers.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("name")}</th>
                <th className="py-2">{t("phone")}</th>
                <th className="py-2">{t("comment")}</th>
              </tr>
            </thead>
            <tbody>
              {(suppliers.list.data ?? []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => open(row)}
                  className="cursor-pointer border-t border-[var(--line)] hover:bg-[var(--cream)]"
                >
                  <td className="py-2">{row.name}</td>
                  <td className="py-2">{row.phone || "—"}</td>
                  <td className="py-2 text-[var(--muted-2)]">{row.comment || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>
      </Card>
      {draft !== null ? (
        <EditorDialog
          open
          onOpenChange={(value) => (value ? null : close())}
          onCancel={null}
          title={editingId === null ? t("newSupplier") : draft.name}
          pending={suppliers.save.isPending}
          error={suppliers.save.error ?? suppliers.remove.error}
          submitLabel={t("save")}
          onSubmit={() =>
            suppliers.save.mutate(
              { id: editingId, body: { name: draft.name.trim(), phone: draft.phone.trim(), comment: draft.comment } },
              { onSuccess: close },
            )
          }
          onDelete={editingId === null ? null : () => suppliers.remove.mutate(editingId, { onSuccess: close })}
          deletePending={suppliers.remove.isPending}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("name")}>
              <Input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            </Field>
            <Field label={t("phone")}>
              <Input value={draft.phone} onChange={(event) => setDraft({ ...draft, phone: event.target.value })} />
            </Field>
            <Field label={t("comment")} className="sm:col-span-2">
              <Textarea value={draft.comment} onChange={(event) => setDraft({ ...draft, comment: event.target.value })} />
            </Field>
          </div>
        </EditorDialog>
      ) : null}
    </div>
  );
}

export function SuppliersPanel() {
  return (
    <FinanceAuthGate>
      <SuppliersList />
    </FinanceAuthGate>
  );
}
