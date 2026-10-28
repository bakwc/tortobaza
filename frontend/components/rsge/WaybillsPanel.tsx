"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Truck } from "lucide-react";
import { QueryState, formatQuantity } from "@/components/menu/ui";
import {
  RsgeChip,
  RsgeDayHeader,
  RsgeDocumentRow,
  RsgeEmpty,
  RsgeSummary,
  groupRsgeByDate,
  rsgeDateKey,
  rsgeMonth,
  rsgeTone,
  sumGel,
  type RsgeColumn,
  type RsgeToneName,
} from "@/components/rsge/RsgeDocumentRow";
import { WaybillSupplyDialog } from "@/components/rsge/WaybillSupplyDialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { Link } from "@/i18n/navigation";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { useDecideWaybill, useWaybills } from "@/hooks/useWaybills";
import { formatCrmCompactDate, formatMoney } from "@/lib/format";
import type { RsWaybill, RsWaybillGood } from "@/lib/api/types";

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

function waybillToneName(waybill: RsWaybill): RsgeToneName {
  if (waybill.is_confirmed === 0) return "pending";
  if (waybill.is_confirmed === -1 || waybill.status === -1 || waybill.status === -2) return "rejected";
  if (waybill.is_confirmed === 1) return "confirmed";
  return "neutral";
}

function waybillPending(waybill: RsWaybill): boolean {
  return waybill.is_confirmed === 0;
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

function WaybillMeta({ waybill, locale }: { waybill: RsWaybill; locale: string }) {
  const t = useTranslations("rsge");
  const start = localized(locale, waybill.start_address, waybill.start_address_ru);
  const end = localized(locale, waybill.end_address, waybill.end_address_ru);
  const driver = localized(locale, waybill.driver_name, waybill.driver_name_ru);
  const rows: { label: string; value: string }[] = [];
  if (start !== "" || end !== "") {
    rows.push({ label: t("route"), value: `${start} → ${end}` });
  }
  if (driver !== "") rows.push({ label: t("driver"), value: driver });
  if (waybill.car_number !== "") rows.push({ label: t("car"), value: waybill.car_number });
  if (rows.length === 0) return null;
  return (
    <div className="grid gap-1.5 text-sm">
      {rows.map((row) => (
        <p key={row.label}>
          <span className="font-medium text-[var(--muted-2)]">{row.label}</span>
          <span className="mx-1.5 text-[var(--ink)]/40">·</span>
          <span className="text-[var(--ink)]">{row.value}</span>
        </p>
      ))}
    </div>
  );
}

export function WaybillsPanel() {
  const t = useTranslations("rsge");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const period = useFinancePeriod();
  const waybills = useWaybills(period.month);
  const decide = useDecideWaybill();
  const [decision, setDecision] = useState<{ id: number; action: "confirm" | "reject" } | null>(null);
  const [supplyWaybill, setSupplyWaybill] = useState<RsWaybill | null>(null);
  const focusedWaybillId = searchParams.get("waybill");

  function openDecision(id: number, action: "confirm" | "reject") {
    decide.reset();
    setDecision({ id, action });
  }

  const columns: RsgeColumn[] = [
    { label: t("name"), align: "left" },
    { label: t("quantity"), align: "right" },
    { label: t("unit"), align: "left" },
    { label: t("price"), align: "right" },
    { label: t("amount"), align: "right" },
    { label: t("barcode"), align: "left" },
  ];

  const documents = waybills.data ?? [];
  const groups = groupRsgeByDate(documents, (waybill) => rsgeDateKey(waybill.create_date), waybillPending);

  useEffect(() => {
    if (focusedWaybillId === null || waybills.isLoading) return;
    const el = document.getElementById(`rsge-waybill-${focusedWaybillId}`);
    if (el === null) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusedWaybillId, waybills.isLoading, documents.length]);

  const pendingCount = documents.filter(waybillPending).length;

  let list: ReactNode = <RsgeEmpty>{t("empty")}</RsgeEmpty>;
  if (documents.length > 0) {
    list = (
      <div className="grid gap-6">
        <RsgeSummary
          count={documents.length}
          total={formatMoney(sumGel(documents.map((waybill) => waybill.full_amount)), "GEL")}
          pending={pendingCount}
        />
        {groups.map((day) => (
          <section key={day.date} className="grid gap-2">
            <RsgeDayHeader
              date={day.date}
              count={day.items.length}
              sum={formatMoney(sumGel(day.items.map((waybill) => waybill.full_amount)), "GEL")}
            />
            {day.items.map((waybill) => {
              const toneName = waybillToneName(waybill);
              const tone = rsgeTone(toneName);
              const pending = waybillPending(waybill);
              return (
                <RsgeDocumentRow
                  key={waybill.id}
                  id={`rsge-waybill-${waybill.id}`}
                  tone={tone}
                  icon={<Truck className="h-4 w-4" />}
                  title={localized(locale, waybill.seller_name, waybill.seller_name_ru)}
                  subtitle={waybill.waybill_number}
                  amount={formatMoney(waybill.full_amount, "GEL")}
                  chips={
                    <>
                      <RsgeChip href={null} className={tone.chip}>{waybillStatus(waybill.status, t)}</RsgeChip>
                      {waybill.is_confirmed === 1 ? (
                        <RsgeChip href={null} className="bg-black/[0.04] text-emerald-700">{t("confirmed")}</RsgeChip>
                      ) : null}
                      {waybill.is_confirmed === -1 ? (
                        <RsgeChip href={null} className="bg-black/[0.04] text-rose-700">{t("rejected")}</RsgeChip>
                      ) : null}
                      <RsgeChip href={null} className="bg-black/[0.04] text-[var(--muted-2)]">
                        {t("positions", { count: waybill.goods.length })}
                      </RsgeChip>
                      {waybill.invoices.map((invoice) => (
                        <RsgeChip
                          key={invoice.id}
                          href={`/rsge/invoices?month=${rsgeMonth(invoice.reg_dt)}&invoice=${invoice.id}`}
                          className="bg-sky-100 text-sky-900"
                        >
                          {t("invoiceBadge")} {invoice.series} {invoice.number}{" "}
                          {formatMoney(invoice.amount, "GEL")}
                        </RsgeChip>
                      ))}
                      {waybill.financial_transactions.map((transaction) => (
                        <RsgeChip
                          key={transaction.id}
                          href={`/finance?month=${transaction.date.slice(0, 7)}&transaction=${transaction.id}`}
                          className="bg-violet-100 text-violet-900"
                        >
                          {t("paymentBadge")} {formatCrmCompactDate(transaction.date, locale)}{" "}
                          {formatMoney(transaction.amount, "GEL")} {transaction.counterparty_name}
                        </RsgeChip>
                      ))}
                    </>
                  }
                  onConfirm={pending ? () => openDecision(waybill.id, "confirm") : null}
                  onReject={pending ? () => openDecision(waybill.id, "reject") : null}
                  details={<WaybillMeta waybill={waybill} locale={locale} />}
                  extra={
                    <div className="flex justify-end border-t border-black/5 pt-3">
                      {waybill.supply_id !== null ? (
                        <Button size="sm" variant="outline" asChild>
                          <Link href="/inventory/supplies">{t("supplyCreated")}</Link>
                        </Button>
                      ) : (
                        <Button type="button" size="sm" variant="outline" onClick={() => setSupplyWaybill(waybill)}>
                          {t("createSupply")}
                        </Button>
                      )}
                    </div>
                  }
                  columns={columns}
                  rowKeys={waybill.goods.map((good) => good.id)}
                  rows={waybill.goods.map((good) => [
                    localized(locale, good.name, good.name_ru),
                    formatQuantity(good.quantity),
                    unitLabel(good, locale),
                    formatMoney(good.price, "GEL"),
                    formatMoney(good.amount, "GEL"),
                    good.bar_code,
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
      <QueryState isLoading={waybills.isLoading} isError={waybills.isError}>
        {list}
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
      {supplyWaybill !== null ? (
        <WaybillSupplyDialog key={supplyWaybill.id} waybill={supplyWaybill} onClose={() => setSupplyWaybill(null)} />
      ) : null}
    </>
  );
}
