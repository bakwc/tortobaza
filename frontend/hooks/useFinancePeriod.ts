"use client";

import { useSearchParams } from "next/navigation";
import { usePathname, useRouter } from "@/i18n/navigation";
import { getTbilisiTodayIsoDate } from "@/lib/format";

export type FinancePeriod = {
  month: string;
  query: string;
  setMonth: (next: string) => void;
};

export function shiftFinanceMonth(yyyyMm: string, delta: number): string {
  const [yearStr, monthStr] = yyyyMm.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  const nextYear = date.getUTCFullYear();
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `${nextYear}-${nextMonth}`;
}

function searchWithMonth(current: string, month: string): string {
  const params = new URLSearchParams(current);
  params.delete("date");
  params.set("month", month);
  return params.toString();
}

export function useFinancePeriod(): FinancePeriod {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const today = getTbilisiTodayIsoDate();
  const month = searchParams.get("month") ?? today.slice(0, 7);

  const setMonth = (next: string) => {
    router.replace(`${pathname}?${searchWithMonth(searchParams.toString(), next)}`);
  };

  return { month, query: `month=${month}`, setMonth };
}
