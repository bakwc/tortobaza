"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Card, QueryState, formatQuantity } from "@/components/menu/ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useDecideWaybill, useWaybills } from "@/hooks/useWaybills";
import { formatCrmDateTime, formatMoney } from "@/lib/format";
import type { RsWaybillGood } from "@/lib/api/types";

function waybillStatus(status: number, t: ReturnType<typeof useTranslations<"rsge">>): string {
  if (status === 0) return t("statusSaved");
  if (status === 1) return t("statusActive");
  if (status === 2) return t("statusCompleted");
  if (status === 8) return t("statusSentToTransporter");
  if (status === -1) return t("statusDeleted");
  if (status === -2) return t("statusCancelled");
  return String(status);
}

function localized(locale: string, original: string, ru: string): string {
  if (locale === "ru" && ru !== "") return ru;
  return original;
}

function unitLabel(good: RsWaybillGood, locale: string): string {
  const unit = localized(locale, good.unit_txt, good.unit_txt_ru);
  if (unit !== "") return unit;
  return String(good.unit_id);
}

function WaybillDecisionDialog({
  action,
  onOpenChange,
  onConfirm,
  isPending,
  isError,
}: {
  action: "confirm" | "reject";
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  isPending: boolean;
  isError: boolean;
}) {
  const t = useTranslations("rsge");
  const rejecting = action === "reject";

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(420px,calc(100vw-1.5rem))] max-w-[420px] p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
          {rejecting ? t("rejectTitle") : t("confirmTitle")}
        </DialogTitle>
        {isError ? <p className="mt-3 text-sm text-[var(--danger)]">{t("decideError")}</p> : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            {t("cancel")}
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className={rejecting ? "bg-[var(--danger)] text-white hover:bg-[var(--danger)]/90" : undefined}
          >
            {isPending ? <Spinner className="h-4 w-4" /> : rejecting ? t("reject") : t("confirm")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function WaybillsPanel() {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const period = useFinancePeriod();
  const waybills = useWaybills(period.month);
  const decide = useDecideWaybill();
  const [decision, setDecision] = useState<{ id: number; action: "confirm" | "reject" } | null>(null);

  function openDecision(id: number, action: "confirm" | "reject") {
    decide.reset();
    setDecision({ id, action });
  }

  return (
    <>
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
                    <span className="font-medium text-[var(--ink)]/80">
                      {" · "}
                      {localized(locale, waybill.seller_name, waybill.seller_name_ru)}
                    </span>
                  </p>
                  <p className="text-sm text-[var(--ink)]/70">
                    {t("status")} {waybillStatus(waybill.status, t)}
                  </p>
                  {waybill.is_confirmed === 1 ? (
                    <p className="text-sm text-[var(--ink)]/70">{t("confirmed")}</p>
                  ) : null}
                  {waybill.is_confirmed === -1 ? (
                    <p className="text-sm text-[var(--ink)]/70">{t("rejected")}</p>
                  ) : null}
                  {waybill.is_confirmed === 0 ? (
                    <div className="mt-1 flex gap-2">
                      <Button type="button" size="sm" onClick={() => openDecision(waybill.id, "confirm")}>
                        {t("confirm")}
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => openDecision(waybill.id, "reject")}>
                        {t("reject")}
                      </Button>
                    </div>
                  ) : null}
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
                      <td className="py-2 pr-3 text-[var(--ink)]">
                        {localized(locale, good.name, good.name_ru)}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 tabular-nums text-[var(--ink)]">
                        {formatQuantity(good.quantity)}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 text-[var(--ink)]/80">{unitLabel(good, locale)}</td>
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
      {decision ? (
        <WaybillDecisionDialog
          action={decision.action}
          isPending={decide.isPending}
          isError={decide.isError}
          onOpenChange={(open) => {
            if (!open) {
              decide.reset();
              setDecision(null);
            }
          }}
          onConfirm={() => {
            decide.mutate(
              { id: decision.id, action: decision.action },
              { onSuccess: () => setDecision(null) },
            );
          }}
        />
      ) : null}
    </>
  );
}
