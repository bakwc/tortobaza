"use client";

import { useLocale, useTranslations } from "next-intl";
import { Card, QueryState, formatQuantity } from "@/components/menu/ui";
import { useWaybills } from "@/hooks/useWaybills";
import { formatCrmDateTime, formatMoney } from "@/lib/format";
import type { RsWaybillGood } from "@/lib/api/types";

function unitLabel(good: RsWaybillGood): string {
  if (good.unit_txt !== "") return good.unit_txt;
  return String(good.unit_id);
}

export function WaybillsPanel() {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const waybills = useWaybills();

  return (
    <QueryState isLoading={waybills.isLoading} isError={waybills.isError}>
      {waybills.data?.length ? (
        <div className="grid gap-4">
          {waybills.data.map((waybill) => (
            <Card key={waybill.id} className="grid gap-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="grid gap-1">
                  <p className="text-sm text-[var(--ink)]/70">{formatCrmDateTime(waybill.create_date, locale)}</p>
                  <p className="text-base font-semibold text-[var(--ink)]">
                    {waybill.waybill_number}
                    <span className="font-medium text-[var(--ink)]/80"> · {waybill.seller_name}</span>
                  </p>
                  <p className="text-sm text-[var(--ink)]/70">
                    {t("status")} {waybill.status}
                  </p>
                </div>
                <p className="text-base font-semibold tabular-nums text-[var(--ink)]">
                  {formatMoney(waybill.full_amount, "GEL")}
                </p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-[var(--ink)]/50">
                    <th className="py-2 pr-3 font-medium">{t("name")}</th>
                    <th className="py-2 pr-3 font-medium">{t("quantity")}</th>
                    <th className="py-2 pr-3 font-medium">{t("unit")}</th>
                    <th className="py-2 pr-3 font-medium">{t("price")}</th>
                    <th className="py-2 pr-3 font-medium">{t("amount")}</th>
                    <th className="py-2 font-medium">{t("barcode")}</th>
                  </tr>
                </thead>
                <tbody>
                  {waybill.goods.map((good) => (
                    <tr key={good.id} className="border-t border-[var(--line)]">
                      <td className="py-2 pr-3 text-[var(--ink)]">{good.name}</td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                        {formatQuantity(good.quantity)}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 text-[var(--ink)]/80">{unitLabel(good)}</td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                        {formatMoney(good.price, "GEL")}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                        {formatMoney(good.amount, "GEL")}
                      </td>
                      <td className="py-2 text-[var(--ink)]/80">{good.bar_code}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--ink)]/70">{t("empty")}</p>
      )}
    </QueryState>
  );
}
