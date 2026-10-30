"use client";

import { useTranslations } from "next-intl";
import { Spinner } from "@/components/ui/spinner";
import { Metric, Note, Section } from "@/components/analytics/widgets";
import { useAnalyticsEmployees } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsEmployees } from "@/lib/api/types";

export function EmployeesPanel() {
  const t = useTranslations("analytics");
  const period = useFinancePeriod();
  const query = useAnalyticsEmployees(period.month);

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

  const report = query.data;
  if (report.employees.length === 0) {
    return <Note>{t("employeesEmpty")}</Note>;
  }

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label={t("hours")} value={formatAmount(report.totals.hours)} hint={null} />
        <Metric label={t("salary")} value={formatMoney(report.totals.money, "GEL")} hint={null} />
        <Metric label={t("placed")} value={String(report.totals.placed)} hint={null} />
        <Metric label={t("made")} value={String(report.totals.made)} hint={null} />
        <Metric label={t("madeKilograms")} value={formatAmount(report.totals.made_kilograms)} hint={null} />
        <Metric label={t("delivered")} value={String(report.totals.delivered)} hint={null} />
      </div>
      <Section title={t("employees")}>
        <EmployeeTable report={report} />
      </Section>
    </div>
  );
}

function EmployeeTable({ report }: { report: AnalyticsEmployees }) {
  const t = useTranslations("analytics");
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="py-2 pr-3 font-medium">{t("name")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("hours")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("salary")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("placed")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("made")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("madeKilograms")}</th>
            <th className="py-2 text-right font-medium">{t("delivered")}</th>
          </tr>
        </thead>
        <tbody>
          {report.employees.map((row) => (
            <tr key={row.id} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3 font-medium">{row.name}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.hours)}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.money, "GEL")}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.placed}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.made}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.made_kilograms)}</td>
              <td className="py-2 text-right tabular-nums">{row.delivered}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
