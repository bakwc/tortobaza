"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CrmAuthGate } from "@/components/crm/CrmAuthGate";
import { CrmOrdersMap } from "@/components/crm/CrmOrdersMap";
import { CrmOverflowMenu } from "@/components/crm/CrmOverflowMenu";
import { MondayDatePicker } from "@/components/crm/MondayDatePicker";
import { Link, useRouter } from "@/i18n/navigation";
import { useCrmMapOrders } from "@/hooks/useCrmOrders";
import { getTbilisiTodayIsoDate } from "@/lib/format";
import type { CrmMapOrderRange } from "@/lib/api/types";

function shiftDate(isoDate: string, days: number): string {
  const [yearStr, monthStr, dayStr] = isoDate.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  const nextDay = String(date.getUTCDate()).padStart(2, "0");
  return `${nextYear}-${nextMonth}-${nextDay}`;
}

function mapQuery(
  dateParam: string | null,
  rangeParam: string | null,
): { range: CrmMapOrderRange | null; date: string | null } {
  if (dateParam !== null) {
    return { range: null, date: dateParam };
  }
  if (rangeParam === "today") {
    return { range: "today", date: null };
  }
  return { range: "next_3_hours", date: null };
}

export default function CrmMapPage() {
  return (
    <div className="flex h-[100dvh] min-h-0 flex-col overflow-hidden px-3 py-3 md:px-4 md:py-4">
      <CrmAuthGate>
        <Suspense
          fallback={
            <div className="flex min-h-0 flex-1 items-center justify-center">
              <Spinner className="h-6 w-6 text-[var(--brand)]" />
            </div>
          }
        >
          <CrmMapBoard />
        </Suspense>
      </CrmAuthGate>
    </div>
  );
}

function CrmMapBoard() {
  const t = useTranslations("crm");
  const router = useRouter();
  const searchParams = useSearchParams();
  const todayStr = getTbilisiTodayIsoDate();
  const query = mapQuery(searchParams.get("date"), searchParams.get("range"));
  const selectedDate = query.date ?? todayStr;
  const isNext3Hours = query.range === "next_3_hours";
  const isToday = selectedDate === todayStr;
  const ordersQuery = useCrmMapOrders(query.range, query.date);
  const orders = ordersQuery.data?.orders ?? [];

  const setSelectedDate = (next: string) => {
    router.replace(`/crm/map?date=${next}`);
  };

  const setNext3Hours = () => {
    router.replace("/crm/map?range=next_3_hours");
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="relative z-20 flex flex-wrap items-center justify-between gap-2">
        <Button
          size="sm"
          variant={isNext3Hours ? "primary" : "outline"}
          onClick={setNext3Hours}
        >
          {t("mapNext3Hours")}
        </Button>
        <div className="flex flex-wrap justify-end gap-2">
          <Button asChild variant="outline">
            <Link href="/crm">{t("dailyBoard")}</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/crm/month">{t("monthlyOrders")}</Link>
          </Button>
          <CrmOverflowMenu />
        </div>
      </div>
      <div className="relative z-20 flex flex-col items-center justify-between gap-3 sm:flex-row">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}
          className="flex items-center gap-1.5"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>{t("previousDay")}</span>
        </Button>

        <div className="flex w-full max-w-md flex-col items-center gap-1 text-center">
          <MondayDatePicker value={selectedDate} onChange={setSelectedDate} />
          <div className="flex items-center gap-2">
            {isToday && !isNext3Hours ? (
              <span className="rounded-full bg-[var(--brand)]/15 px-2.5 py-0.5 text-xs font-semibold text-[var(--brand)]">
                {t("today")}
              </span>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedDate(todayStr)}
                className="h-7 text-xs font-medium text-[var(--brand)] hover:text-[var(--brand)]"
              >
                {isToday ? t("today") : t("jumpToToday")}
              </Button>
            )}
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}
          className="flex items-center gap-1.5"
        >
          <span>{t("nextDay")}</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-3xl border border-[var(--line)] bg-white shadow-sm">
        {ordersQuery.isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Spinner className="h-8 w-8 text-[var(--brand)]" />
          </div>
        ) : ordersQuery.isError ? (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-[var(--danger)]">
            {t("mapLoadError")}
          </div>
        ) : (
          <>
            <CrmOrdersMap orders={orders} />
            {orders.length === 0 ? (
              <div className="pointer-events-none absolute inset-x-0 top-4 z-10 flex justify-center px-4">
                <div className="pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl border border-[var(--line)] bg-white/95 px-4 py-3 shadow-md">
                  <Package className="mt-0.5 h-5 w-5 shrink-0 text-[var(--muted)]" />
                  <div>
                    <p className="text-sm font-semibold text-[var(--ink)]">
                      {t("mapEmptyTitle")}
                    </p>
                    <p className="text-xs text-[var(--muted-2)]">{t("mapEmptyHint")}</p>
                  </div>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
