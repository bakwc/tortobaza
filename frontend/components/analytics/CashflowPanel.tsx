"use client";

import { useTranslations } from "next-intl";
import { Section } from "@/components/analytics/widgets";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsCashflow } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatMoney } from "@/lib/format";
import type { AnalyticsCashflow } from "@/lib/api/types";

const BOX = "border border-[var(--line)] py-2";

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
  const showInvesting = Number(report.investing.total) !== 0;
  const showFinancing = Number(report.financing.total) !== 0;
  const showUnclassified = Number(report.unclassified.total) !== 0;
  const showTransfers = Number(report.transfers) !== 0;

  return (
    <div className="overflow-x-auto bg-white">
      <table className="w-full border-collapse bg-white text-sm">
        <thead>
          <tr>
            <th className={`${BOX} px-3 text-left font-semibold`}>{t("cashflowItem")}</th>
            <th className={`${BOX} px-3 text-right font-semibold`}>{t("cashflowAmount")}</th>
          </tr>
        </thead>
        <tbody>
          <Line label={t("cashflowOpening")} amount={report.opening} strong pad="" />
          <Group label={t("cashflowOperating")} />
          {report.operating.inflows.length > 0 ? <Sub label={t("cashflowInflows")} /> : null}
          {report.operating.inflows.map((line) => (
            <Line
              key={`in-${line.key}`}
              label={line.key === "" ? t("cashflowUnclassifiedIncome") : finance(`incomeTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          {report.operating.outflows.length > 0 ? <Sub label={t("cashflowOutflows")} /> : null}
          {report.operating.outflows.map((line) => (
            <Line
              key={`out-${line.key}`}
              label={line.key === "" ? t("cashflowUnclassifiedExpense") : finance(`expenseTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          <Line label={t("cashflowOperatingTotal")} amount={report.operating.total} strong pad="pl-4" />
          {showInvesting ? (
            <>
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
            </>
          ) : null}
          {showFinancing ? (
            <>
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
            </>
          ) : null}
          {showUnclassified ? (
            <>
              <Group label={t("cashflowUnclassified")} />
              {report.unclassified.lines.map((line) => (
                <Line
                  key={line.key}
                  label={finance(`kinds.${line.key}`)}
                  amount={line.amount}
                  strong={false}
                  pad="pl-8"
                />
              ))}
              <Line label={t("cashflowUnclassifiedTotal")} amount={report.unclassified.total} strong pad="pl-4" />
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

function Group({ label }: { label: string }) {
  return (
    <tr className="font-semibold">
      <td className={`${BOX} px-3`}>{label}</td>
      <td className={`${BOX} px-3`} />
    </tr>
  );
}

function Sub({ label }: { label: string }) {
  return (
    <tr>
      <td className={`${BOX} pr-3 pl-6 text-[var(--muted)]`}>{label}</td>
      <td className={`${BOX} px-3`} />
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
  const weight = strong ? "font-semibold" : "";
  return (
    <tr>
      <td className={`${BOX} pr-3 ${pad === "" ? "pl-3" : pad} ${weight}`}>{label}</td>
      <td className={`${BOX} px-3 text-right tabular-nums ${weight}`}>{formatMoney(amount, "GEL")}</td>
    </tr>
  );
}
