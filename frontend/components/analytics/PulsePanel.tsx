"use client";

import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsPulse } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount, formatMoney } from "@/lib/format";
import {
  AXIS_TICK,
  COLOR_ORDERS,
  COLOR_REVENUE,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  dayLabel,
  deltaText,
} from "@/components/analytics/widgets";

const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

export function PulsePanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const period = useFinancePeriod();
  const query = useAnalyticsPulse(period.month);

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
  const weeks = report.weeks.map((week) => ({
    label: dayLabel(week.start, locale),
    orders: week.orders,
    revenue: Number(week.revenue),
  }));
  const weekdays = report.weekdays.map((row) => ({
    label: t(WEEKDAYS[row.weekday]),
    revenue: Number(row.revenue),
    orders: row.orders,
  }));
  const average =
    report.current.average_check === null ? t("emptyValue") : formatMoney(report.current.average_check, "GEL");
  const averageHint =
    report.current.average_check !== null && report.previous.average_check !== null
      ? deltaText(report.current.average_check, report.previous.average_check, true)
      : null;

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label={t("orders")}
          value={formatAmount(report.current.orders)}
          hint={deltaText(report.current.orders, report.previous.orders, false)}
        />
        <Metric
          label={t("revenue")}
          value={formatMoney(report.current.revenue, "GEL")}
          hint={deltaText(report.current.revenue, report.previous.revenue, true)}
        />
        <Metric label={t("averageCheck")} value={average} hint={averageHint} />
        <Metric
          label={t("kilograms")}
          value={formatAmount(report.current.kilograms)}
          hint={deltaText(report.current.kilograms, report.previous.kilograms, false)}
        />
      </div>
      <Note>
        {t("pulseNote", {
          start: dayLabel(report.previous_start, locale),
          end: dayLabel(report.previous_end, locale),
          count: report.current.weight_unknown,
        })}
      </Note>
      <Section title={t("weeks")}>
        <ChartFrame>
          <BarChart data={weeks} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={16} />
            <YAxis yAxisId="orders" tick={AXIS_TICK} width={36} />
            <YAxis yAxisId="revenue" orientation="right" tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            <Bar yAxisId="orders" dataKey="orders" name={t("orders")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="revenue" dataKey="revenue" name={t("revenue")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("weekdaysTitle")}>
        <ChartFrame>
          <BarChart data={weekdays} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="revenue" name={t("revenue")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
    </div>
  );
}
