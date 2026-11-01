"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

const ACCRUAL_BLANK_ROWS = 7;
const DEDUCTION_BLANK_ROWS = 3;

function dottedDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}

function payslipNumber(amount: string): string {
  const value = Number.parseFloat(amount);
  const negative = value < 0;
  const [intPart, fracPart] = Math.abs(value).toFixed(2).split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negative ? "-" : ""}${grouped},${fracPart}`;
}

function Cell({
  children,
  align,
}: {
  children?: string;
  align?: "right" | "center";
}) {
  return (
    <td
      className={
        align === "right"
          ? "h-7 border border-black px-2 text-right tabular-nums"
          : align === "center"
            ? "h-7 border border-black px-2 text-center"
            : "h-7 border border-black px-2"
      }
    >
      {children ?? ""}
    </td>
  );
}

export function PayslipDocument({
  name,
  position,
  start,
  end,
  hours,
  money,
}: {
  name: string;
  position: string;
  start: string;
  end: string;
  hours: string;
  money: string;
}) {
  const t = useTranslations("crm");
  const amount = payslipNumber(money);
  const hoursLabel = payslipNumber(hours);

  return (
    <div className="mx-auto w-full max-w-[210mm]">
      <div className="mb-6 flex justify-end print:hidden">
        <Button type="button" onClick={() => window.print()}>
          {t("invoicePrint")}
        </Button>
      </div>
      <article className="bg-white p-8 text-sm text-black print:p-0 md:p-12">
        <h1 className="text-lg font-bold uppercase tracking-wide text-[#3d5a80]">Расчетный листок</h1>
        <p className="mt-4">
          За период: {dottedDate(start)}-{dottedDate(end)}
        </p>
        <p className="mt-4">Сотрудник: {name}</p>
        <p className="mt-4">Должность: {position}</p>

        <table className="mt-4 w-full border-collapse border border-black">
          <colgroup>
            <col className="w-[34%]" />
            <col className="w-[28%]" />
            <col className="w-[18%]" />
            <col className="w-[20%]" />
          </colgroup>
          <thead>
            <tr>
              <Cell align="center">Вид начисления</Cell>
              <Cell align="center">Период</Cell>
              <Cell align="center">Часы/Дни</Cell>
              <Cell align="center">Сумма, GEL</Cell>
            </tr>
          </thead>
          <tbody>
            <tr>
              <Cell>Заработная плата</Cell>
              <Cell />
              <Cell align="right">{hoursLabel}</Cell>
              <Cell align="right">{amount}</Cell>
            </tr>
            {Array.from({ length: ACCRUAL_BLANK_ROWS }, (_, index) => (
              <tr key={index}>
                <Cell />
                <Cell />
                <Cell />
                <Cell />
              </tr>
            ))}
          </tbody>
        </table>

        <table className="mt-8 w-full border-collapse border border-black">
          <colgroup>
            <col className="w-[62%]" />
            <col className="w-[38%]" />
          </colgroup>
          <thead>
            <tr>
              <Cell align="center">Удержания</Cell>
              <Cell align="center">Сумма, GEL</Cell>
            </tr>
          </thead>
          <tbody>
            <tr>
              <Cell>Нет</Cell>
              <Cell>-</Cell>
            </tr>
            {Array.from({ length: DEDUCTION_BLANK_ROWS }, (_, index) => (
              <tr key={index}>
                <Cell />
                <Cell />
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-8 space-y-4">
          <p>Всего начислено: {amount} GEL</p>
          <p>Всего удержано: 0 GEL</p>
          <p>К выплате: {amount} GEL</p>
          <p>Подпись сотрудника: ______________</p>
          <p>Подпись Директор Харламова Д. О.: ______________</p>
          <p>Подпись Финансовый Директор Баканов Ф. И. ______________</p>
        </div>
      </article>
    </div>
  );
}
