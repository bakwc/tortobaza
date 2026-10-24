"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Card, QueryState, formatQuantity } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useDecideInvoice, useInvoices } from "@/hooks/useInvoices";
import { formatCrmDateTime, formatMoney } from "@/lib/format";

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

  return (
    <>
      <QueryState isLoading={invoices.isLoading} isError={invoices.isError}>
        {invoices.data?.length ? (
          <div className="grid gap-4">
            {invoices.data.map((invoice) => (
              <Card key={invoice.id} className="grid gap-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="grid gap-1">
                    <p className="text-sm text-[var(--ink)]/70">{formatCrmDateTime(invoice.reg_dt, locale)}</p>
                    <p className="text-base font-semibold text-[var(--ink)]">
                      {invoice.series} {invoice.number}
                      <span className="font-medium text-[var(--ink)]/80">
                        {" · "}
                        {localized(locale, invoice.org_name, invoice.org_name_ru)}
                      </span>
                    </p>
                    <p className="text-sm text-[var(--ink)]/70">
                      {t("status")} {invoiceStatus(invoice.status, t)}
                    </p>
                    {invoice.was_ref === 1 ? (
                      <p className="text-sm text-[var(--ink)]/70">{t("rejected")}</p>
                    ) : null}
                    {PENDING_STATUSES.has(invoice.status) && invoice.was_ref === 0 ? (
                      <div className="mt-1 flex gap-2">
                        <Button type="button" size="sm" onClick={() => openDecision(invoice.id, "confirm")}>
                          {t("confirm")}
                        </Button>
                        <Button type="button" size="sm" variant="outline" onClick={() => openDecision(invoice.id, "reject")}>
                          {t("reject")}
                        </Button>
                      </div>
                    ) : null}
                    {invoice.notes !== "" ? (
                      <p className="text-sm text-[var(--ink)]/80">
                        {localized(locale, invoice.notes, invoice.notes_ru)}
                      </p>
                    ) : null}
                  </div>
                  <p className="text-base font-semibold tabular-nums text-[var(--ink)]">
                    {formatMoney(invoice.amount, "GEL")}
                  </p>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                      <th className="py-2 pr-3 font-medium">{t("name")}</th>
                      <th className="py-2 pr-3 font-medium">{t("quantity")}</th>
                      <th className="py-2 pr-3 font-medium">{t("unit")}</th>
                      <th className="py-2 pr-3 font-medium">{t("amount")}</th>
                      <th className="py-2 font-medium">{t("vat")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.lines.map((line) => (
                      <tr key={line.id} className="border-t border-[var(--line)]">
                        <td className="py-2 pr-3 text-[var(--ink)]">
                          {localized(locale, line.goods, line.goods_ru)}
                        </td>
                        <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                          {formatQuantity(line.quantity)}
                        </td>
                        <td className="whitespace-nowrap py-2 pr-3 text-[var(--ink)]/80">
                          {localized(locale, line.unit, line.unit_ru)}
                        </td>
                        <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                          {formatMoney(line.full_amount, "GEL")}
                        </td>
                        <td className="whitespace-nowrap py-2 tabular-nums text-[var(--ink)]">
                          {formatMoney(line.vat_amount, "GEL")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--ink)]/70">{t("invoicesEmpty")}</p>
        )}
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
