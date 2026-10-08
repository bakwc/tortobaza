"use client";

import { useSearchParams } from "next/navigation";
import { usePathname, useRouter } from "@/i18n/navigation";
import { getTbilisiTodayIsoDate } from "@/lib/format";

export type FinancePeriodMode = "day" | "month";

export type FinancePeriod = {
  mode: FinancePeriodMode;
  date: string;
  month: string;
  query: string;
  setDate: (next: string) => void;
  setMonth: (next: string) => void;
  setMode: (mode: FinancePeriodMode) => void;
};

export function shiftFinanceDate(isoDate: string, days: number): string {
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

export function shiftFinanceMonth(yyyyMm: string, delta: number): string {
  const [yearStr, monthStr] = yyyyMm.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${nextYear}-${nextMonth}`;
}

export function useFinancePeriod(): FinancePeriod {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const today = getTbilisiTodayIsoDate();
  const monthParam = searchParams.get("month");
  const dateParam = searchParams.get("date");
  const mode: FinancePeriodMode = monthParam !== null ? "month" : "day";
  const date =
    dateParam ??
    (monthParam ? (monthParam === today.slice(0, 7) ? today : `${monthParam}-01`) : today);
  const month = monthParam ?? date.slice(0, 7);

  const setDate = (next: string) => {
    router.replace(`${pathname}?date=${next}`);
  };

  const setMonth = (next: string) => {
    router.replace(`${pathname}?month=${next}`);
  };

  const setMode = (next: FinancePeriodMode) => {
    if (next === "month") {
      router.replace(`${pathname}?month=${date.slice(0, 7)}`);
      return;
    }
    const day = month === today.slice(0, 7) ? today : `${month}-01`;
    router.replace(`${pathname}?date=${day}`);
  };

  const query = mode === "month" ? `month=${month}` : `date=${date}`;

  return { mode, date, month, query, setDate, setMonth, setMode };
}
