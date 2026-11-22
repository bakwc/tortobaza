"use client";

import { useTranslations } from "next-intl";
import { Section } from "@/components/analytics/widgets";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsPnl } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatMoney } from "@/lib/format";
import type { AnalyticsPnl } from "@/lib/api/types";

const BOX = "border border-[var(--line)] py-2";

export function PnlPanel() {
  const t = useTranslations("analytics");
  const period = useFinancePeriod();
  const query = useAnalyticsPnl(period.month);

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
    <Section title={t("pnlStatement")}>
      <PnlTable report={query.data} />
    </Section>
  );
}

function cogsLabel(key: string, t: ReturnType<typeof useTranslations>): string {
  if (key === "unlinked_products") {
    return t("pnlCogsUnlinkedProducts");
  }
  if (key === "orders") {
    return t("pnlCogsOrders");
  }
  if (key === "write_offs") {
    return t("pnlCogsWriteOffs");
  }
  if (key === "supply_gap") {
    return t("pnlCogsSupplyGap");
  }
  if (key === "inventory") {
    return t("pnlCogsInventory");
  }
  throw new Error(key);
}

function PnlTable({ report }: { report: AnalyticsPnl }) {
  const t = useTranslations("analytics");
  const finance = useTranslations("finance");
  const showUnclassified = Number(report.unclassified.total) !== 0;
  const showCogs = report.expenses.cogs.lines.length > 0;

  return (
    <div className="overflow-x-auto bg-white">
      <table className="w-full border-collapse bg-white text-sm">
        <thead>
          <tr>
            <th className={`${BOX} px-3 text-left font-semibold`}>{t("pnlItem")}</th>
            <th className={`${BOX} px-3 text-right font-semibold`}>{t("pnlAmount")}</th>
          </tr>
        </thead>
        <tbody>
          <Group label={t("pnlIncome")} />
          {report.income.lines.map((line) => (
            <Line
              key={`in-${line.key}`}
              label={line.key === "" ? t("cashflowUnclassifiedIncome") : finance(`incomeTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          <Line label={t("pnlIncomeTotal")} amount={report.income.total} strong pad="pl-4" />
          <Group label={t("pnlExpenses")} />
          {report.expenses.lines.map((line) => (
            <Line
              key={`out-${line.key}`}
              label={line.key === "" ? t("cashflowUnclassifiedExpense") : finance(`expenseTypes.${line.key}`)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          {showCogs ? <Sub label={t("pnlCogs")} /> : null}
          {report.expenses.cogs.lines.map((line) => (
            <Line
              key={`cogs-${line.key}`}
              label={cogsLabel(line.key, t)}
              amount={line.amount}
              strong={false}
              pad="pl-8"
            />
          ))}
          {showCogs ? (
            <Line label={t("pnlCogsTotal")} amount={report.expenses.cogs.total} strong pad="pl-4" />
          ) : null}
          <Line label={t("pnlExpensesTotal")} amount={report.expenses.total} strong pad="pl-4" />
          {showUnclassified ? (
            <>
              <Group label={t("pnlUnclassified")} />
              {report.unclassified.lines.map((line) => (
                <Line
                  key={line.key}
                  label={finance(`kinds.${line.key}`)}
                  amount={line.amount}
                  strong={false}
                  pad="pl-8"
                />
              ))}
              <Line label={t("pnlUnclassifiedTotal")} amount={report.unclassified.total} strong pad="pl-4" />
            </>
          ) : null}
          <Line label={t("pnlProfit")} amount={report.profit} strong pad="" />
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
