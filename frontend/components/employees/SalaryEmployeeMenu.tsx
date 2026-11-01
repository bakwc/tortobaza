"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { FileText, List, MoreHorizontal } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Link } from "@/i18n/navigation";
import { useCrmSalaryDetail } from "@/hooks/useCrmOrders";
import { formatAed } from "@/lib/format";

function formatDay(iso: string, locale: string): string {
  const tag = locale === "ka" ? "ka-GE" : locale === "ru" ? "ru-RU" : "en-GB";
  return new Date(`${iso}T00:00:00`).toLocaleDateString(tag, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatClock(iso: string | null): string {
  if (iso === null) return "";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Asia/Tbilisi",
  }).format(new Date(iso));
}

export function SalaryEmployeeMenu({
  userId,
  name,
  start,
  end,
}: {
  userId: number;
  name: string;
  start: string;
  end: string;
}) {
  const t = useTranslations("crm");
  const employeesT = useTranslations("employees");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const detailQuery = useCrmSalaryDetail(userId, start, end, detailOpen);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="h-8 w-8 shrink-0 px-0"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={t("salaryActions")}
        aria-expanded={open}
      >
        <MoreHorizontal className="h-4 w-4" />
      </Button>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 min-w-[180px] rounded-2xl border border-[var(--line)] bg-white py-1 shadow-lg">
          <Link
            href={`/employees/salaries/${userId}/payslip?start=${start}&end=${end}`}
            target="_blank"
            rel="noreferrer"
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => setOpen(false)}
          >
            <FileText className="h-4 w-4" />
            {t("salaryPayslip")}
          </Link>
          <button
            type="button"
            className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-[var(--ink)] hover:bg-[var(--cream)]"
            onClick={() => {
              setOpen(false);
              setDetailOpen(true);
            }}
          >
            <List className="h-4 w-4" />
            {t("salaryDetail")}
          </button>
        </div>
      ) : null}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="w-[min(720px,calc(100vw-1.5rem))] overflow-y-auto p-6">
          <DialogTitle className="pr-10 text-base font-semibold text-[var(--ink)]">
            {t("salaryDetail")}: {name}
          </DialogTitle>
          {detailQuery.isError ? (
            <p className="mt-4 text-sm text-[var(--danger)]">{t("salaryDetailLoadError")}</p>
          ) : !detailQuery.data ? (
            <div className="flex min-h-40 items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          ) : (
            <div className="mt-4">
              <p className="text-sm font-medium text-[var(--ink)]">
                {detailQuery.data.monthly
                  ? t("salaryDetailRateMonthly", { rate: formatAed(detailQuery.data.monthly_rate) })
                  : t("salaryDetailRateHourly", { rate: formatAed(detailQuery.data.hourly_rate) })}
              </p>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[28rem] text-sm">
                  <thead>
                    <tr className="border-b border-[var(--line)] text-left text-xs font-medium uppercase tracking-wide text-[var(--ink)]/60">
                      <th className="pb-3 pr-4 font-medium">{employeesT("date")}</th>
                      <th className="pb-3 pr-4 font-medium">{t("salaryArrival")}</th>
                      <th className="pb-3 pr-4 font-medium">{t("salaryDeparture")}</th>
                      <th className="pb-3 pr-4 font-medium">{t("salaryHours")}</th>
                      <th className="pb-3 font-medium">{t("salaryEarned")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--line)]">
                    {detailQuery.data.rows.map((row) => (
                      <tr key={row.date}>
                        <td className="py-2 pr-4 text-[var(--ink)]">{formatDay(row.date, locale)}</td>
                        <td className="py-2 pr-4 tabular-nums text-[var(--ink)]">{formatClock(row.arrival)}</td>
                        <td className="py-2 pr-4 tabular-nums text-[var(--ink)]">{formatClock(row.departure)}</td>
                        <td className="py-2 pr-4 tabular-nums font-medium text-[var(--ink)]">{row.hours}</td>
                        <td className="py-2 tabular-nums font-medium text-[var(--ink)]">{formatAed(row.money)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-[var(--line)]">
                      <td className="pt-3 pr-4 font-semibold text-[var(--ink)]" colSpan={3}>
                        {t("salaryMonthTotal")}
                      </td>
                      <td className="pt-3 pr-4 tabular-nums font-semibold text-[var(--ink)]">
                        {detailQuery.data.total_hours}
                      </td>
                      <td className="pt-3 tabular-nums font-semibold text-[var(--ink)]">
                        {formatAed(detailQuery.data.total_money)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
