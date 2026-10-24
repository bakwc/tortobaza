"use client";

import { useState, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { FileText } from "lucide-react";
import { QueryState, formatQuantity } from "@/components/menu/ui";
import {
  RsgeChip,
  RsgeDayHeader,
  RsgeDocumentRow,
  RsgeEmpty,
  RsgeSummary,
  groupRsgeByDate,
  rsgeDateKey,
  rsgeTone,
  sumGel,
  type RsgeColumn,
  type RsgeToneName,
} from "@/components/rsge/RsgeDocumentRow";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useDecideInvoice, useInvoices } from "@/hooks/useInvoices";
import { formatMoney } from "@/lib/format";
import type { RsInvoice } from "@/lib/api/types";

const PENDING_STATUSES = new Set([1, 5, 6]);

function invoiceStatus(status: number, t: ReturnType<typeof useTranslations<"rsge">>): string {
  if (status === 0) return t("invoiceStatusNew");
  if (status === 1) return t("invoiceStatusSent");
  if (status === 2) return t("invoiceStatusConfirmed");
  if (status === 3) return t("invoiceStatusCorrectedPrimary");
  if (status === 4) return t("invoiceStatusCorrection");
  if (status === 5) return t("invoiceStatusCorrectionSent");
  if (status === 6) return t("invoiceStatusCancelled");
  if (status === 7) return t("invoiceStatusCancellationConfirmed");
  if (status === 8) return t("invoiceStatusCorrectionConfirmed");
  return String(status);
}

function localized(locale: string, original: string, ru: string): string {
  if (locale === "ru" && ru !== "") return ru;
  return original;
}

function invoicePending(invoice: RsInvoice): boolean {
  return PENDING_STATUSES.has(invoice.status) && invoice.was_ref === 0;
}

function invoiceToneName(invoice: RsInvoice): RsgeToneName {
  if (invoicePending(invoice)) return "pending";
  if (invoice.was_ref === 1 || invoice.status === 7) return "rejected";
  if (invoice.status === 2 || invoice.status === 8) return "confirmed";
  return "neutral";
}

function InvoiceDecisionDialog({
  action,
  onOpenChange,
  onConfirm,
  isPending,
  isError,
}: {
  action: "confirm" | "reject";
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations("rsge");
  const [reason, setReason] = useState("");
  const rejecting = action === "reject";
  const reasonMissing = rejecting && reason.trim() === "";

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
          {rejecting ? t("invoiceRejectTitle") : t("invoiceConfirmTitle")}
        </DialogTitle>
        {rejecting ? (
          <label className="mt-4 grid gap-2 text-sm text-[var(--ink)]">
            {t("rejectReason")}
            <Textarea value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
        ) : null}
        {isError ? <p className="mt-3 text-sm text-[var(--danger)]">{t("decideError")}</p> : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            {t("cancel")}
          </Button>
          <Button
            type="button"
            onClick={() => onConfirm(reason.trim())}
            disabled={isPending || reasonMissing}
            className={rejecting ? "bg-[var(--danger)] text-white hover:bg-[var(--danger)]/90" : undefined}
          >
            {isPending ? <Spinner className="h-4 w-4" /> : rejecting ? t("reject") : t("confirm")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function InvoiceNotes({ invoice, locale }: { invoice: RsInvoice; locale: string }) {
  const t = useTranslations("rsge");
  const notes = localized(locale, invoice.notes, invoice.notes_ru);
  if (notes === "") return null;
  return (
    <p className="text-sm text-[var(--ink)]">
      <span className="font-medium text-[var(--muted-2)]">{t("notes")}</span>
      <span className="mx-1.5 text-[var(--ink)]/40">·</span>
      {notes}
    </p>
  );
}

export function InvoicesPanel() {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const period = useFinancePeriod();
  const invoices = useInvoices(period.month);
  const decide = useDecideInvoice();
  const [decision, setDecision] = useState<{ id: number; action: "confirm" | "reject" } | null>(null);

  function openDecision(id: number, action: "confirm" | "reject") {
    decide.reset();
    setDecision({ id, action });
  }

  const columns: RsgeColumn[] = [
    { label: t("name"), align: "left" },
    { label: t("quantity"), align: "right" },
    { label: t("unit"), align: "left" },
    { label: t("amount"), align: "right" },
    { label: t("vat"), align: "right" },
  ];

  const documents = invoices.data ?? [];
  const groups = groupRsgeByDate(documents, (invoice) => rsgeDateKey(invoice.reg_dt), invoicePending);
  const pendingCount = documents.filter(invoicePending).length;

  let list: ReactNode = <RsgeEmpty>{t("invoicesEmpty")}</RsgeEmpty>;
  if (documents.length > 0) {
    list = (
      <div className="grid gap-6">
        <RsgeSummary
          count={documents.length}
          total={formatMoney(sumGel(documents.map((invoice) => invoice.amount)), "GEL")}
          pending={pendingCount}
        />
        {groups.map((day) => (
          <section key={day.date} className="grid gap-2">
            <RsgeDayHeader
              date={day.date}
              count={day.items.length}
              sum={formatMoney(sumGel(day.items.map((invoice) => invoice.amount)), "GEL")}
            />
            {day.items.map((invoice) => {
              const toneName = invoiceToneName(invoice);
              const tone = rsgeTone(toneName);
              const pending = invoicePending(invoice);
              const number = `${invoice.series} ${invoice.number}`.trim();
              return (
                <RsgeDocumentRow
                  key={invoice.id}
                  tone={tone}
                  icon={<FileText className="h-4 w-4" />}
                  title={number}
                  subtitle={localized(locale, invoice.org_name, invoice.org_name_ru)}
                  amount={formatMoney(invoice.amount, "GEL")}
                  chips={
                    <>
                      <RsgeChip className={tone.chip}>{invoiceStatus(invoice.status, t)}</RsgeChip>
                      {invoice.status === 2 || invoice.status === 8 ? (
                        <RsgeChip className="bg-white/80 text-emerald-800">{t("confirmed")}</RsgeChip>
                      ) : null}
                      {invoice.was_ref === 1 ? (
                        <RsgeChip className="bg-white/80 text-rose-800">{t("rejected")}</RsgeChip>
                      ) : null}
                      <RsgeChip className="bg-white/80 text-[var(--ink)]">
                        {t("vat")} {formatMoney(invoice.vat, "GEL")}
                      </RsgeChip>
                      <RsgeChip className="bg-white/80 text-[var(--muted-2)]">
                        {t("positions", { count: invoice.lines.length })}
                      </RsgeChip>
                    </>
                  }
                  onConfirm={pending ? () => openDecision(invoice.id, "confirm") : null}
                  onReject={pending ? () => openDecision(invoice.id, "reject") : null}
                  details={<InvoiceNotes invoice={invoice} locale={locale} />}
                  columns={columns}
                  rowKeys={invoice.lines.map((line) => line.id)}
                  rows={invoice.lines.map((line) => [
                    localized(locale, line.goods, line.goods_ru),
                    formatQuantity(line.quantity),
                    localized(locale, line.unit, line.unit_ru),
                    formatMoney(line.full_amount, "GEL"),
                    formatMoney(line.vat_amount, "GEL"),
                  ])}
                />
              );
            })}
          </section>
        ))}
      </div>
    );
  }

  return (
    <>
      <QueryState isLoading={invoices.isLoading} isError={invoices.isError}>
        {list}
      </QueryState>
      {decision ? (
        <InvoiceDecisionDialog
          action={decision.action}
          isPending={decide.isPending}
          isError={decide.isError}
          onOpenChange={(open) => {
            if (!open) {
              decide.reset();
              setDecision(null);
            }
          }}
          onConfirm={(reason) => {
            decide.mutate(
              decision.action === "confirm"
                ? { id: decision.id, action: "confirm" }
                : { id: decision.id, action: "reject", refText: reason },
              { onSuccess: () => setDecision(null) },
            );
          }}
        />
      ) : null}
    </>
  );
}
