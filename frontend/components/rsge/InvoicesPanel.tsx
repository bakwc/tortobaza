"use client";

import { useLocale, useTranslations } from "next-intl";
import { Card, QueryState, formatQuantity } from "@/components/menu/ui";
import { useInvoices } from "@/hooks/useInvoices";
import { formatCrmDateTime, formatMoney } from "@/lib/format";

export function InvoicesPanel() {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const invoices = useInvoices();

  return (
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
                    <span className="font-medium text-[var(--ink)]/80"> · {invoice.org_name}</span>
                  </p>
                  <p className="text-sm text-[var(--ink)]/70">
                    {t("status")} {invoice.status}
                  </p>
                  {invoice.notes !== "" ? <p className="text-sm text-[var(--ink)]/80">{invoice.notes}</p> : null}
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
                      <td className="py-2 pr-3 text-[var(--ink)]">{line.goods}</td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                        {formatQuantity(line.quantity)}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 text-[var(--ink)]/80">{line.unit}</td>
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
  );
}
