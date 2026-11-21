"use client";

import { useTranslations } from "next-intl";
import { Section } from "@/components/analytics/widgets";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsCashflow } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatMoney } from "@/lib/format";
import type { AnalyticsCashflow } from "@/lib/api/types";

export function CashflowPanel() {
  const t = useTranslations("analytics");
  const period = useFinancePeriod();
  const query = useAnalyticsCashflow(period.month);

  if (query.isError) {
    return <p className="text-sm text-[var(--danger)]">{t("loadError")}</p>;
  }
  if (!query.data) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner className="h-6 w-6 text-[var(--brand)]" />
      </div>
    );
  }

  return (
    <Section title={t("cashflowStatement")}>
      <CashflowTable report={query.data} />
    </Section>
  );
}

function CashflowTable({ report }: { report: AnalyticsCashflow }) {
  const t = useTranslations("analytics");
  const finance = useTranslations("finance");
  const showUnclassified = Number(report.unclassified.total) !== 0;
  const showTransfers = Number(report.transfers) !== 0;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <tbody>
          <Line label={t("cashflowOpening")} amount={report.opening} strong pad="" />
          <Group label={t("cashflowOperating")} />
          {report.operating.inflows.length > 0 ? <Sub label={t("cashflowInflows")} /> : null}
          {report.operating.inflows.map((line) => (
            <Line
              key={line.key}
              label={finance(`incomeTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          {report.operating.outflows.length > 0 ? <Sub label={t("cashflowOutflows")} /> : null}
          {report.operating.outflows.map((line) => (
            <Line
              key={line.key}
              label={finance(`expenseTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          <Line label={t("cashflowOperatingTotal")} amount={report.operating.total} strong pad="pl-4" />
          <Group label={t("cashflowInvesting")} />
          {report.investing.lines.map((line) => (
            <Line
              key={line.key}
              label={finance(`expenseTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          <Line label={t("cashflowInvestingTotal")} amount={report.investing.total} strong pad="pl-4" />
          <Group label={t("cashflowFinancing")} />
          {report.financing.lines.map((line) => (
            <Line
              key={line.key}
              label={finance(`kinds.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          <Line label={t("cashflowFinancingTotal")} amount={report.financing.total} strong pad="pl-4" />
          {showUnclassified ? (
            <>
              <Group label={t("cashflowUnclassified")} />
              {report.unclassified.lines.map((line) => (
                <Line
                  key={line.key}
                  label={unclassifiedLabel(line.key, t, finance)}
                  amount={line.amount}
                  strong={false}
                  pad="pl-8"
                />
              ))}
              <Line
                label={t("cashflowUnclassifiedTotal")}
                amount={report.unclassified.total}
                strong
                pad="pl-4"
              />
            </>
          ) : null}
          <Line label={t("cashflowNet")} amount={report.net} strong pad="" />
          {showTransfers ? (
            <Line label={t("cashflowTransfers")} amount={report.transfers} strong={false} pad="" />
          ) : null}
          <Line label={t("cashflowClosing")} amount={report.closing} strong pad="" />
        </tbody>
      </table>
    </div>
  );
}

function unclassifiedLabel(
  key: string,
  t: ReturnType<typeof useTranslations>,
  finance: ReturnType<typeof useTranslations>,
): string {
  if (key === "income") return t("cashflowUnclassifiedIncome");
  if (key === "expense") return t("cashflowUnclassifiedExpense");
  return finance(`kinds.${key}`);
}

function Group({ label }: { label: string }) {
  return (
    <tr>
      <td colSpan={2} className="pt-4 pb-1 font-semibold text-[var(--ink)]">
        {label}
      </td>
    </tr>
  );
}

function Sub({ label }: { label: string }) {
  return (
    <tr>
      <td colSpan={2} className="py-1 pl-4 text-[var(--muted)]">
        {label}
      </td>
    </tr>
  );
}

function Line({
  label,
  amount,
  strong,
  pad,
}: {
  label: string;
  amount: string;
  strong: boolean;
  pad: string;
}) {
  return (
    <tr className="border-t border-[var(--line)]">
      <td className={`py-2 pr-3 ${pad} ${strong ? "font-semibold" : ""}`}>{label}</td>
      <td className={`py-2 text-right tabular-nums ${strong ? "font-semibold" : ""}`}>
        {formatMoney(amount, "GEL")}
      </td>
    </tr>
  );
}
