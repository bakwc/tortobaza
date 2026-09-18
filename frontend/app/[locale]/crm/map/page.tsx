"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Columns3,
  Package,
  PackageCheck,
} from "lucide-react";
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
  if (rangeParam === "next_3_hours") {
    return { range: "next_3_hours", date: null };
  }
  return { range: "today", date: null };
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
  const [hideDelivered, setHideDelivered] = useState(false);
  const ordersQuery = useCrmMapOrders(query.range, query.date);
  const orders = ordersQuery.data?.orders ?? [];
  const visibleOrders = hideDelivered
    ? orders.filter((order) => order.status !== "delivered")
    : orders;

  const setSelectedDate = (next: string) => {
    router.replace(`/crm/map?date=${next}`);
  };

  const setNext3Hours = () => {
    router.replace("/crm/map?range=next_3_hours");
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 md:gap-3">
      <div className="relative z-20 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center rounded-full bg-[var(--cream)] p-1">
          <Button
            size="sm"
            variant={isNext3Hours ? "primary" : "ghost"}
            onClick={setNext3Hours}
            className="h-8 gap-1.5 px-3"
          >
            <Clock3 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{t("mapNext3Hours")}</span>
            <span className="sm:hidden">{t("mapNext3HoursShort")}</span>
          </Button>
          <Button
            size="sm"
            variant={!isNext3Hours && isToday ? "primary" : "ghost"}
            onClick={() => setSelectedDate(todayStr)}
            className="h-8 px-3"
          >
            {t("today")}
          </Button>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Button asChild variant="outline" size="icon" className="h-9 w-9 md:w-auto md:px-4">
            <Link href="/crm" aria-label={t("dailyBoard")} title={t("dailyBoard")}>
              <Columns3 className="h-4 w-4 md:mr-1.5" />
              <span className="hidden md:inline">{t("dailyBoard")}</span>
            </Link>
          </Button>
          <Button asChild variant="outline" size="icon" className="h-9 w-9 md:w-auto md:px-4">
            <Link href="/crm/month" aria-label={t("monthlyOrders")} title={t("monthlyOrders")}>
              <CalendarDays className="h-4 w-4 md:mr-1.5" />
              <span className="hidden md:inline">{t("monthlyOrders")}</span>
            </Link>
          </Button>
          <CrmOverflowMenu />
        </div>
      </div>
      <div className="relative z-20 grid grid-cols-[44px_minmax(0,1fr)_44px] items-center gap-2 md:mx-auto md:w-full md:max-w-xl">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setSelectedDate(shiftDate(selectedDate, -1))}
          aria-label={t("previousDay")}
          title={t("previousDay")}
          className="h-11 w-11"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <div className="min-w-0 [&>div]:w-full">
          <MondayDatePicker value={selectedDate} onChange={setSelectedDate} />
        </div>

        <Button
          variant="outline"
          size="icon"
          onClick={() => setSelectedDate(shiftDate(selectedDate, 1))}
          aria-label={t("nextDay")}
          title={t("nextDay")}
          className="h-11 w-11"
        >
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
            <CrmOrdersMap orders={visibleOrders} />
            <Button
              type="button"
              size="sm"
              variant={hideDelivered ? "primary" : "soft"}
              onClick={() => setHideDelivered((value) => !value)}
              aria-pressed={hideDelivered}
              className="absolute right-3 top-3 z-10 gap-1.5 shadow-md"
            >
              <PackageCheck className="h-4 w-4" />
              {t("mapHideDelivered")}
            </Button>
            {visibleOrders.length === 0 ? (
              <div className="pointer-events-none absolute inset-x-0 top-16 z-10 flex justify-center px-4">
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
