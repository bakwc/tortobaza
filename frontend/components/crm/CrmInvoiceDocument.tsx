"use client";

import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import type { CrmOrder } from "@/lib/api/types";
import { formatAed, formatCrmDate } from "@/lib/format";
import { SITE_INFO } from "@/lib/site-info";

export function CrmInvoiceDocument({ order }: { order: CrmOrder }) {
  const t = useTranslations("crm");
  const locale = useLocale();
  const priceNum = Number.parseFloat(order.cake_price);
  const prepayNum = Number.parseFloat(order.prepayment);
  const remainingNum = Math.max(0, priceNum - prepayNum);
  const companyAddress = `${SITE_INFO.address.line1}, ${SITE_INFO.address.city}, ${SITE_INFO.address.country}`;

  return (
    <div className="mx-auto w-full max-w-[210mm]">
      <div className="mb-6 flex justify-end print:hidden">
        <Button type="button" onClick={() => window.print()}>
          {t("invoicePrint")}
        </Button>
      </div>
      <article className="rounded-none border border-[var(--line)] bg-white p-8 text-[var(--ink)] shadow-sm print:border-0 print:p-0 print:shadow-none md:p-12">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--line)] pb-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink)]/60">
              {t("invoiceTitle")}
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-wide">
              {t("invoiceNumber", { id: order.id })}
            </h1>
          </div>
          <p className="text-sm">
            <span className="text-[var(--ink)]/60">{t("invoiceDate")}: </span>
            {formatCrmDate(order.date, locale)}
          </p>
        </header>

        <div className="mt-8 grid gap-8 sm:grid-cols-2">
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink)]/60">
              {t("invoiceFrom")}
            </h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoiceTradingName")}</dt>
                <dd className="font-semibold">{SITE_INFO.brand}</dd>
              </div>
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoiceCompanyName")}</dt>
                <dd>{SITE_INFO.legalName}</dd>
              </div>
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoiceCompanyId")}</dt>
                <dd>{SITE_INFO.legalId}</dd>
              </div>
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoiceEmail")}</dt>
                <dd>{SITE_INFO.email}</dd>
              </div>
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoicePhone")}</dt>
                <dd>{SITE_INFO.phone}</dd>
              </div>
              <div>
                <dt className="text-[var(--ink)]/60">{t("invoiceCompanyAddress")}</dt>
                <dd>{companyAddress}</dd>
              </div>
            </dl>
          </section>

          <section>
            <h2 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink)]/60">
              {t("invoiceBillTo")}
            </h2>
            <div className="mt-3 space-y-1 text-sm">
              <p className="font-semibold">{order.contact}</p>
              {order.nickname ? <p>{order.nickname}</p> : null}
              {order.fulfillment_type === "delivery" && order.delivery_address ? (
                <p>{order.delivery_address}</p>
              ) : null}
            </div>
          </section>
        </div>

        <section className="mt-8">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--line)] text-left text-xs font-semibold uppercase tracking-[0.06em] text-[var(--ink)]/60">
                <th className="py-2 pr-4 font-semibold">{t("invoiceItem")}</th>
                <th className="py-2 text-right font-semibold">{t("invoiceAmount")}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--line)] align-top">
                <td className="py-4 pr-4">
                  <p className="font-semibold">
                    {order.weight}
                    {order.filling ? ` · ${order.filling}` : ""}
                  </p>
                  {order.description ? (
                    <p className="mt-1 whitespace-pre-wrap text-[var(--ink)]/80">{order.description}</p>
                  ) : null}
                </td>
                <td className="py-4 text-right font-semibold tabular-nums">{formatAed(order.cake_price)}</td>
              </tr>
            </tbody>
          </table>
          <dl className="ml-auto mt-4 w-full max-w-xs space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ink)]/60">{t("price")}</dt>
              <dd className="tabular-nums">{formatAed(order.cake_price)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ink)]/60">{t("prepaid")}</dt>
              <dd className="tabular-nums">{formatAed(order.prepayment)}</dd>
            </div>
            <div className="flex justify-between gap-4 border-t border-[var(--line)] pt-2 font-semibold">
              <dt>{t("remaining")}</dt>
              <dd className="tabular-nums">{formatAed(remainingNum)}</dd>
            </div>
          </dl>
        </section>

        <section className="mt-10 border-t border-[var(--line)] pt-6">
          <h2 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ink)]/60">
            {t("invoicePaymentDetails")}
          </h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="grid gap-1 sm:grid-cols-[9rem_1fr]">
              <dt className="font-semibold">Address</dt>
              <dd>{SITE_INFO.bank.address}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[9rem_1fr]">
              <dt className="font-semibold">IBAN</dt>
              <dd className="font-medium tabular-nums">{SITE_INFO.bank.iban}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[9rem_1fr]">
              <dt className="font-semibold">SWIFT</dt>
              <dd className="font-medium">{SITE_INFO.bank.swift}</dd>
            </div>
            <div className="grid gap-1 sm:grid-cols-[9rem_1fr]">
              <dt className="font-semibold">Receiver Name</dt>
              <dd>{SITE_INFO.bank.receiverName}</dd>
            </div>
          </dl>
        </section>
      </article>
    </div>
  );
}
