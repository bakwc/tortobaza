"use client";

import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsLoad } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount } from "@/lib/format";
import {
  AXIS_TICK,
  COLOR_HEAVY,
  COLOR_ORDERS,
  COLOR_REVENUE,
  COLOR_USUAL,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  dayLabel,
} from "@/components/analytics/widgets";
import type { AnalyticsLoad } from "@/lib/api/types";

export function LoadPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const period = useFinancePeriod();
  const query = useAnalyticsLoad(period.month);

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
  const days = report.days.map((day) => ({
    label: dayLabel(day.date, locale),
    orders: day.orders,
    kilograms: Number(day.kilograms),
  }));
  const hours = report.slots.hours.map((row) => ({
    label: String(row.hour),
    orders: row.orders,
  }));

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric
          label={t("usualDay")}
          value={baselineValue(report, "orders_median", "kilograms_median") ?? t("emptyValue")}
          hint={null}
        />
        <Metric
          label={t("heavyDay")}
          value={baselineValue(report, "orders_p90", "kilograms_p90") ?? t("emptyValue")}
          hint={null}
        />
        <Metric
          label={t("maxDay")}
          value={baselineValue(report, "orders_max", "kilograms_max") ?? t("emptyValue")}
          hint={null}
        />
      </div>
      <Note>{t("loadNote", { days: report.baseline.days })}</Note>
      <Section title={t("orders")}>
        <ChartFrame>
          <BarChart data={days} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={16} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="orders" name={t("orders")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
            {report.baseline.orders_median !== null ? (
              <ReferenceLine
                y={Number(report.baseline.orders_median)}
                stroke={COLOR_USUAL}
                strokeDasharray="4 4"
                label={t("usualDay")}
              />
            ) : null}
            {report.baseline.orders_p90 !== null ? (
              <ReferenceLine
                y={Number(report.baseline.orders_p90)}
                stroke={COLOR_HEAVY}
                strokeDasharray="4 4"
                label={t("heavyDay")}
              />
            ) : null}
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("kilograms")}>
        <ChartFrame>
          <BarChart data={days} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={16} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="kilograms" name={t("kilograms")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
            {report.baseline.kilograms_median !== null ? (
              <ReferenceLine
                y={Number(report.baseline.kilograms_median)}
                stroke={COLOR_USUAL}
                strokeDasharray="4 4"
                label={t("usualDay")}
              />
            ) : null}
            {report.baseline.kilograms_p90 !== null ? (
              <ReferenceLine
                y={Number(report.baseline.kilograms_p90)}
                stroke={COLOR_HEAVY}
                strokeDasharray="4 4"
                label={t("heavyDay")}
              />
            ) : null}
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("horizon")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Metric
            label={t("tomorrow")}
            value={t("horizonValue", {
              orders: report.horizon.tomorrow.orders,
              kilograms: formatAmount(report.horizon.tomorrow.kilograms),
            })}
            hint={dayLabel(report.horizon.tomorrow.date, locale)}
          />
          <Metric
            label={t("dayAfter")}
            value={t("horizonValue", {
              orders: report.horizon.day_after.orders,
              kilograms: formatAmount(report.horizon.day_after.kilograms),
            })}
            hint={dayLabel(report.horizon.day_after.date, locale)}
          />
        </div>
      </Section>
      <Section title={t("slots")}>
        <Note>{t("allTime")}</Note>
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric label={t("interval")} value={formatAmount(report.slots.interval)} hint={null} />
          <Metric label={t("exact")} value={formatAmount(report.slots.exact)} hint={null} />
          <Metric label={t("missingTime")} value={formatAmount(report.slots.missing)} hint={null} />
          <Metric label={t("morning")} value={formatAmount(report.slots.morning)} hint={null} />
          <Metric label={t("daytime")} value={formatAmount(report.slots.day)} hint={null} />
          <Metric label={t("evening")} value={formatAmount(report.slots.evening)} hint={null} />
        </div>
        <ChartFrame>
          <BarChart data={hours} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={12} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="orders" name={t("orders")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("lead")}>
        <Note>{t("allTime")}</Note>
        <div className="grid gap-3 sm:grid-cols-4">
          <Metric
            label={t("leadMedian")}
            value={report.lead.median === null ? t("emptyValue") : formatAmount(report.lead.median)}
            hint={null}
          />
          <Metric label={t("sameDay")} value={formatAmount(report.lead.same_day)} hint={null} />
          <Metric label={t("nextDay")} value={formatAmount(report.lead.next_day)} hint={null} />
          <Metric label={t("longLead")} value={formatAmount(report.lead.long)} hint={null} />
        </div>
      </Section>
    </div>
  );
}

function baselineValue(
  report: AnalyticsLoad,
  ordersKey: "orders_median" | "orders_p90" | "orders_max",
  kilogramsKey: "kilograms_median" | "kilograms_p90" | "kilograms_max",
): string | null {
  const orders = report.baseline[ordersKey];
  const kilograms = report.baseline[kilogramsKey];
  if (orders === null || kilograms === null) return null;
  return `${formatAmount(orders)} / ${formatAmount(kilograms)}`;
}
