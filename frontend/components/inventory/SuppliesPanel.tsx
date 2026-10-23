"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { FinanceAuthGate } from "@/components/finance/FinanceAuthGate";
import { newDraftKey } from "@/components/menu/ComponentLinesEditor";
import { SearchSelect } from "@/components/menu/SearchSelect";
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
import { useIngredients, useSuppliers, useSupplies, useSupplyReceiptUpload, useSupplyTransactions } from "@/hooks/useStock";
import type { MenuUnit, Supply, SupplyReceipt } from "@/lib/api/types";
import { getTbilisiTodayIsoDate } from "@/lib/format";

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

type SupplyLineDraft = {
  key: string;
  ingredient: string;
  quantity: string;
  total: string;
  hint: string;
  suggestedName: string;
  suggestedUnit: MenuUnit | null;
};

type ReceiptPreview = { id: number; image: string };

type ReceiptMismatch = { receiptId: number; total: string; lines: string };

type SupplyDraft = {
  date: string;
  supplier: number | null;
  financial_transaction: number | null;
  comment: string;
  lines: SupplyLineDraft[];
  receipts: ReceiptPreview[];
  mismatches: ReceiptMismatch[];
};

function emptyLine(): SupplyLineDraft {
  return {
    key: newDraftKey(),
    ingredient: "",
    quantity: "",
    total: "",
    hint: "",
    suggestedName: "",
    suggestedUnit: null,
  };
}

function draftFrom(row: Supply | null): SupplyDraft {
  if (row === null) {
    return {
      date: getTbilisiTodayIsoDate(),
      supplier: null,
      financial_transaction: null,
      comment: "",
      lines: [],
      receipts: [],
      mismatches: [],
    };
  }
  return {
    date: row.date,
    supplier: row.supplier,
    financial_transaction: row.financial_transaction?.id ?? null,
    comment: row.comment,
    lines: row.lines.map((line) => ({
      key: newDraftKey(),
      ingredient: String(line.ingredient),
      quantity: line.quantity,
      total: line.total,
      hint: "",
      suggestedName: "",
      suggestedUnit: null,
    })),
    receipts: row.receipts.map((receipt) => ({ id: receipt.id, image: receipt.image })),
    mismatches: [],
  };
}

function applyReceipt(draft: SupplyDraft, receipt: SupplyReceipt, dateEdited: boolean): SupplyDraft {
  const recognized = receipt.recognized;
  const added = recognized.lines.map((line) => ({
    key: newDraftKey(),
    ingredient: line.ingredient_id === null ? "" : String(line.ingredient_id),
    quantity: line.quantity,
    total: line.total,
    hint: `${line.name_ru} · ${line.original_name}`,
    suggestedName: line.name_ru,
    suggestedUnit: line.unit,
  }));
  const linesSum = added.reduce((sum, line) => sum + Number(decimal(line.total) || "0"), 0);
  const mismatches = [...draft.mismatches];
  if (recognized.is_itemized && Math.abs(linesSum - Number(recognized.total)) >= 0.01) {
    mismatches.push({ receiptId: receipt.id, total: recognized.total, lines: linesSum.toFixed(2) });
  }
  return {
    ...draft,
    date: !dateEdited && ISO_DATE.test(recognized.date) ? recognized.date : draft.date,
    supplier: draft.supplier === null ? recognized.supplier : draft.supplier,
    receipts: [...draft.receipts, { id: receipt.id, image: receipt.image }],
    lines: [...draft.lines, ...added],
    mismatches,
  };
}

function decimal(value: string): string {
  return value.replace(",", ".");
}

function SupplyEditor({ supply, onClose }: { supply: Supply | null; onClose: () => void }) {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const supplies = useSupplies();
  const suppliers = useSuppliers();
  const ingredients = useIngredients();
  const transactions = useSupplyTransactions(supply ? supply.id : null);
  const receiptUpload = useSupplyReceiptUpload();
  const fileInput = useRef<HTMLInputElement>(null);
  const dateEdited = useRef(supply !== null);
  const [draft, setDraft] = useState<SupplyDraft>(() => draftFrom(supply));
  const [newSupplier, setNewSupplier] = useState("");

  const updateLine = (key: string, patch: Partial<SupplyLineDraft>) =>
    setDraft((prev) => ({ ...prev, lines: prev.lines.map((line) => (line.key === key ? { ...line, ...patch } : line)) }));

  const uploadFiles = (files: File[]) => {
    const [file, ...rest] = files;
    if (file === undefined) {
      return;
    }
    receiptUpload.mutate(file, {
      onSuccess: (receipt) => {
        setDraft((prev) => applyReceipt(prev, receipt, dateEdited.current));
        uploadFiles(rest);
      },
    });
  };

  const total = draft.lines.reduce((sum, line) => sum + Number(decimal(line.total) || "0"), 0);
  const linked = (transactions.data ?? []).find((row) => row.id === draft.financial_transaction);
  const mismatch = linked !== undefined && Math.abs(Math.abs(Number(linked.amount)) - total) >= 0.01;

  return (
    <EditorDialog
      open
      onOpenChange={(value) => (value ? null : onClose())}
      onCancel={null}
      title={supply === null ? t("newSupply") : `${t("inventory.supplies")} · ${supply.date}`}
      pending={supplies.save.isPending}
      error={supplies.save.error ?? supplies.remove.error}
      submitLabel={t("save")}
      onSubmit={() =>
        supplies.save.mutate(
          {
            id: supply ? supply.id : null,
            body: {
              date: draft.date,
              supplier: draft.supplier,
              financial_transaction: draft.financial_transaction,
              comment: draft.comment,
              receipts: draft.receipts.map((receipt) => receipt.id),
              lines: draft.lines.map((line) => ({
                ingredient: Number(line.ingredient),
                quantity: decimal(line.quantity),
                total: decimal(line.total),
              })),
            },
          },
          { onSuccess: onClose },
        )
      }
      onDelete={supply === null ? null : () => supplies.remove.mutate(supply.id, { onSuccess: onClose })}
      deletePending={supplies.remove.isPending}
      below={null}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("date")}>
          <Input
            type="date"
            required
            value={draft.date}
            onChange={(event) => {
              dateEdited.current = true;
              setDraft({ ...draft, date: event.target.value });
            }}
          />
        </Field>
        <Field label={t("supplier")}>
          <NativeSelect
            value={draft.supplier ?? ""}
            onChange={(event) =>
              setDraft({ ...draft, supplier: event.target.value === "" ? null : Number(event.target.value) })
            }
          >
            <option value="">—</option>
            {(suppliers.list.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <div className="flex gap-2 sm:col-span-2">
          <Input
            value={newSupplier}
            placeholder={t("newSupplier")}
            onChange={(event) => setNewSupplier(event.target.value)}
          />
          <Button
            type="button"
            variant="outline"
            disabled={newSupplier.trim() === "" || suppliers.save.isPending}
            onClick={() =>
              suppliers.save.mutate(
                { id: null, body: { name: newSupplier.trim(), phone: "", comment: "" } },
                {
                  onSuccess: (created) => {
                    setNewSupplier("");
                    setDraft((prev) => ({ ...prev, supplier: created.id }));
                  },
                },
              )
            }
          >
            {t("add")}
          </Button>
        </div>
        <ErrorText error={suppliers.save.error} />
        <Field label={t("bankTransaction")} className="sm:col-span-2">
          <NativeSelect
            value={draft.financial_transaction ?? ""}
            onChange={(event) =>
              setDraft({
                ...draft,
                financial_transaction: event.target.value === "" ? null : Number(event.target.value),
              })
            }
          >
            <option value="">{t("noBankTransaction")}</option>
            {(transactions.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.date} · {formatMoney(row.amount)} · {row.counterparty_name || row.description} · {row.account_name}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label={t("comment")} className="sm:col-span-2">
          <Textarea value={draft.comment} onChange={(event) => setDraft({ ...draft, comment: event.target.value })} />
        </Field>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <CardTitle>{t("lines")}</CardTitle>
        <div>
          <input
            ref={fileInput}
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.heic,image/jpeg,image/png,image/heic"
            className="hidden"
            onChange={(event) => {
              const files = event.target.files;
              event.target.value = "";
              if (files !== null && files.length > 0) {
                uploadFiles(Array.from(files));
              }
            }}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={receiptUpload.isPending}
            onClick={() => fileInput.current?.click()}
          >
            {receiptUpload.isPending ? <Spinner className="mr-1 h-4 w-4" /> : null}
            {receiptUpload.isPending ? t("recognizingReceipt") : t("uploadReceipt")}
          </Button>
        </div>
      </div>
      <ErrorText error={receiptUpload.error} />
      {draft.receipts.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {draft.receipts.map((receipt) => (
            <div key={receipt.id} className="relative">
              <a href={receipt.image} target="_blank" rel="noreferrer">
                <img src={receipt.image} alt="" className="h-28 w-28 rounded-xl object-cover" />
              </a>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t("removeReceipt")}
                className="absolute right-1 top-1 bg-white/90"
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    receipts: prev.receipts.filter((row) => row.id !== receipt.id),
                    mismatches: prev.mismatches.filter((row) => row.receiptId !== receipt.id),
                  }))
                }
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      ) : null}
      {draft.mismatches.map((row) => (
        <p key={row.receiptId} className="text-sm font-semibold text-amber-700">
          {t("receiptTotalDiffers", { total: formatMoney(row.total), lines: formatMoney(row.lines) })}
        </p>
      ))}
      <div className="grid gap-2">
        {draft.lines.map((line) => {
          const ingredient = (ingredients.list.data ?? []).find((row) => String(row.id) === line.ingredient);
          const suggestedUnit = line.suggestedUnit;
          return (
            <div key={line.key} className="grid gap-1">
              <div className="grid grid-cols-[1fr_auto] gap-2 sm:grid-cols-[1fr_9rem_9rem_auto]">
                <SearchSelect
                  options={(ingredients.list.data ?? [])
                    .filter((row) => row.is_active || String(row.id) === line.ingredient)
                    .map((row) => ({ value: String(row.id), label: row.name }))}
                  value={line.ingredient}
                  onChange={(ingredient) => updateLine(line.key, { ingredient })}
                  placeholder={t("chooseComponent")}
                  required={true}
                  className="col-span-2 sm:col-span-1"
                />
                <div className="relative">
                  <Input
                    required
                    inputMode="decimal"
                    placeholder={t("quantity")}
                    value={line.quantity}
                    onChange={(event) => updateLine(line.key, { quantity: event.target.value })}
                    className="pr-12"
                  />
                  <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-xs text-[var(--muted-2)]">
                    {ingredient ? units(ingredient.unit) : suggestedUnit !== null ? units(suggestedUnit) : ""}
                  </span>
                </div>
                <Input
                  required
                  inputMode="decimal"
                  placeholder={t("lineTotal")}
                  value={line.total}
                  onChange={(event) => updateLine(line.key, { total: event.target.value })}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("removeLine")}
                  onClick={() =>
                    setDraft((prev) => ({ ...prev, lines: prev.lines.filter((row) => row.key !== line.key) }))
                  }
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              {line.hint !== "" ? <p className="text-xs text-[var(--muted-2)]">{line.hint}</p> : null}
              {line.ingredient === "" && line.suggestedName !== "" && suggestedUnit !== null ? (
                <div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={ingredients.save.isPending}
                    onClick={() => {
                      const body = {
                        name: line.suggestedName,
                        category: null,
                        unit: suggestedUnit,
                        is_active: true,
                        avg_cost: null,
                        cost_quantity: null,
                      };
                      Reflect.deleteProperty(body, "avg_cost");
                      Reflect.deleteProperty(body, "cost_quantity");
                      ingredients.save.mutate(
                        { id: null, body },
                        { onSuccess: (created) => updateLine(line.key, { ingredient: String(created.id) }) },
                      );
                    }}
                  >
                    {t("createIngredient")}
                  </Button>
                </div>
              ) : null}
            </div>
          );
        })}
        <ErrorText error={ingredients.save.error} />
        <div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setDraft((prev) => ({ ...prev, lines: [...prev.lines, emptyLine()] }))}
          >
            <Plus className="mr-1 h-4 w-4" />
            {t("addLine")}
          </Button>
        </div>
      </div>
      <p className={mismatch ? "text-sm font-semibold text-amber-700" : "text-sm text-[var(--ink)]"}>
        {t("total")}: {formatMoney(String(total))}
        {mismatch && linked ? ` · ${t("bankAmountDiffers", { amount: formatMoney(linked.amount) })}` : ""}
      </p>
    </EditorDialog>
  );
}

function SuppliesList() {
  const t = useTranslations("stock");
  const units = useTranslations("stock.units");
  const supplies = useSupplies();
  const [editing, setEditing] = useState<Supply | null | "new">(null);

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>{t("inventory.supplies")}</CardTitle>
          <Button
            type="button"
            size="sm"
            onClick={() => {
              supplies.save.reset();
              setEditing("new");
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            {t("add")}
          </Button>
        </div>
        <QueryState isLoading={supplies.list.isLoading} isError={supplies.list.isError}>
          <div className="mt-4 grid gap-2">
            {(supplies.list.data ?? []).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => {
                  supplies.save.reset();
                  setEditing(row);
                }}
                className="rounded-2xl border border-[var(--line)] px-4 py-3 text-left hover:bg-[var(--cream)]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-[var(--ink)]">
                    {row.date} · {row.supplier_name ?? "—"}
                  </span>
                  <span className="text-sm font-semibold">{formatMoney(row.total)}</span>
                </div>
                <p className="mt-1 text-sm text-[var(--muted-2)]">
                  {row.lines.map((line) => `${line.name} ${formatQuantity(line.quantity)} ${units(line.unit)}`).join(", ")}
                </p>
                {row.financial_transaction ? (
                  <p className="mt-1 text-xs text-emerald-700">
                    {t("bankTransaction")}: {row.financial_transaction.date} · {formatMoney(row.financial_transaction.amount)}
                  </p>
                ) : null}
              </button>
            ))}
          </div>
        </QueryState>
      </Card>
      {editing !== null ? (
        <SupplyEditor supply={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      ) : null}
    </div>
  );
}

export function SuppliesPanel() {
  return (
    <FinanceAuthGate>
      <SuppliesList />
    </FinanceAuthGate>
  );
}
