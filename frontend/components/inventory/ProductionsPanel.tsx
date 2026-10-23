"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EditorDialog } from "@/components/menu/EditorDialog";
import { SearchSelect } from "@/components/menu/SearchSelect";
import { Card, CardTitle, Field, QueryState, formatMoney, formatQuantity } from "@/components/menu/ui";
import { useProductions, useSemiProducts } from "@/hooks/useStock";
import type { Production, ProductionBody } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";

type ProductionDraft = { date: string; semi_product: string; quantity: string; comment: string };

function draftFrom(row: Production | null): ProductionDraft {
  if (row === null) {
    return { date: getTbilisiTodayIsoDate(), semi_product: "", quantity: "", comment: "" };
  }
  return { date: row.date, semi_product: String(row.semi_product), quantity: row.quantity, comment: row.comment };
}

export function ProductionsPanel() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const productions = useProductions();
  const semiProducts = useSemiProducts();
  const [editing, setEditing] = useState<Production | null>(null);
  const [draft, setDraft] = useState<ProductionDraft | null>(null);

  const produced = (semiProducts.list.data ?? []).filter((row) => row.is_produced);
  const selected = produced.find((row) => String(row.id) === draft?.semi_product);

  const open = (row: Production | null) => {
    productions.save.reset();
    productions.remove.reset();
    setEditing(row);
    setDraft(draftFrom(row));
  };
  const close = () => setDraft(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.productions")}</CardTitle>
          <Button type="button" size="sm" onClick={() => open(null)}>
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={productions.list.isLoading} isError={productions.list.isError}>
          <table className="mt-4 w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
              <tr>
                <th className="py-2">{t("date")}</th>
                <th className="py-2">{t("semiProduct")}</th>
                <th className="py-2 text-right">{t("quantity")}</th>
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
                  <td className="py-2">{row.semi_product_name}</td>
                  <td className="py-2 text-right">
                    {formatQuantity(row.quantity)} {units(row.unit)}
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
          title={editing === null ? t("newProduction") : `${editing.semi_product_name} · ${editing.date}`}
          pending={productions.save.isPending}
          error={productions.save.error ?? productions.remove.error}
          submitLabel={t("save")}
          onSubmit={() => {
            const body: ProductionBody = {
              date: draft.date,
              semi_product: Number(draft.semi_product),
              quantity: draft.quantity.replace(",", "."),
              comment: draft.comment,
            };
            productions.save.mutate({ id: editing ? editing.id : null, body }, { onSuccess: close });
          }}
          onDelete={editing === null ? null : () => productions.remove.mutate(editing.id, { onSuccess: close })}
          deletePending={productions.remove.isPending}
          below={null}
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={t("date")}>
              <Input
                type="date"
                required
                value={draft.date}
                onChange={(event) => setDraft({ ...draft, date: event.target.value })}
              />
            </Field>
            <Field label={t("semiProduct")}>
              <SearchSelect
                options={produced.map((row) => ({ value: String(row.id), label: row.name }))}
                value={draft.semi_product}
                onChange={(semi_product) => setDraft({ ...draft, semi_product })}
                placeholder={t("chooseComponent")}
                required={true}
                className=""
              />
            </Field>
            <Field label={selected ? `${t("quantity")}, ${units(selected.unit)}` : t("quantity")}>
              <Input
                required
                inputMode="decimal"
                value={draft.quantity}
                onChange={(event) => setDraft({ ...draft, quantity: event.target.value })}
              />
            </Field>
            <Field label={t("comment")} className="sm:col-span-3">
              <Textarea value={draft.comment} onChange={(event) => setDraft({ ...draft, comment: event.target.value })} />
            </Field>
          </div>
          {produced.length === 0 ? <p className="text-sm text-[var(--muted-2)]">{t("noProducedSemiProducts")}</p> : null}
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
              {editing.unit_cost ? (
                <p className="text-sm text-[var(--ink)]">
                  {t("unitCost")}: {formatMoney(editing.unit_cost)}
                </p>
              ) : null}
            </div>
          ) : null}
        </EditorDialog>
      ) : null}
    </div>
  );
}
