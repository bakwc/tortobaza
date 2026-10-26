"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsOverview } from "@/hooks/useAnalytics";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsOverviewPayment } from "@/lib/api/types";
import {
  AXIS_TICK,
  COLOR_NEW,
  COLOR_ORDERS,
  COLOR_REVENUE,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  dayLabel,
  deltaText,
  monthLabel,
} from "@/components/analytics/widgets";

const PAYMENT_LABELS: Record<AnalyticsOverviewPayment["type"], string> = {
  unknown: "paymentTypes.unknown",
  cash: "paymentTypes.cash",
  terminal: "paymentTypes.terminal",
  tbc: "paymentTypes.tbc",
  bog: "paymentTypes.bog",
  tbank: "paymentTypes.tbank",
  flowwow: "paymentTypes.flowwow",
  crypto: "paymentTypes.crypto",
  paypal: "paymentTypes.paypal",
  online: "paymentTypes.online",
};

type ChannelMetric = "revenue" | "orders";

type MonthPoint = {
  label: string;
  partial: boolean;
  orders: number;
  revenue: number;
  average: number | null;
  kilograms: number;
  pricePerKg: number | null;
};

function ordersBarLabel(value: number): string {
  return formatAmount(value);
}

function revenueBarLabel(value: number): string {
  return formatMoney(value, "GEL").replace(".00", "");
}

function barTopCenter(viewBox: unknown): { x: number; y: number } | null {
  if (typeof viewBox !== "object" || viewBox === null) return null;
  const box = viewBox as { x?: unknown; y?: unknown; width?: unknown; upperWidth?: unknown };
  const x = Number(box.x);
  const y = Number(box.y);
  const width = Number(box.upperWidth ?? box.width);
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(width)) return null;
  return { x: x + width / 2, y: y - 8 };
}

function BarValueLabel({
  viewBox,
  value,
  format,
}: {
  viewBox?: unknown;
  value?: unknown;
  format: (value: number) => string;
}) {
  const point = barTopCenter(viewBox);
  if (point === null || typeof value !== "number" || Number.isNaN(value)) return null;
  return (
    <text x={point.x} y={point.y} fill="#666666" fontSize={12} textAnchor="middle">
      {format(value)}
    </text>
  );
}

function linePoints(points: MonthPoint[], key: "average" | "pricePerKg") {
  const lastPartial = points.length > 0 && points[points.length - 1].partial;
  return points.map((point, index) => {
    const value = point[key];
    const isLast = index === points.length - 1;
    const isJoin = lastPartial && index === points.length - 2;
    return {
      label: point.label,
      solid: isLast && lastPartial ? null : value,
      dashed: isLast || isJoin ? value : null,
    };
  });
}

export function OverviewPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const query = useAnalyticsOverview();
  const [channelMetric, setChannelMetric] = useState<ChannelMetric>("revenue");

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
  const partialLabel = t("partial");
  const points: MonthPoint[] = report.months.map((row) => ({
    label: row.partial ? `${monthLabel(row.month, locale)} · ${partialLabel}` : monthLabel(row.month, locale),
    partial: row.partial,
    orders: row.orders,
    revenue: Number(row.revenue),
    average: row.average_check === null ? null : Number(row.average_check),
    kilograms: Number(row.kilograms),
    pricePerKg: row.price_per_kg === null ? null : Number(row.price_per_kg),
  }));
  const channels = report.channels.map((row, index) => ({
    label: points[index].label,
    partial: points[index].partial,
    flowwow: Number(row.flowwow[channelMetric]),
    website: Number(row.website[channelMetric]),
    direct: Number(row.direct[channelMetric]),
  }));
  const paymentRevenue = report.payments.reduce((sum, row) => sum + Number(row.revenue), 0);
  const payments = [...report.payments].reverse().map((row) => {
    const share = paymentRevenue === 0 ? 0 : Math.round((Number(row.revenue) / paymentRevenue) * 100);
    return {
      label: `${t(PAYMENT_LABELS[row.type])} · ${share}%`,
      revenue: Number(row.revenue),
    };
  });
  const average =
    report.totals.average_check === null ? t("emptyValue") : formatMoney(report.totals.average_check, "GEL");
  const since = report.first_date === null ? null : t("since", { date: dayLabel(report.first_date, locale) });
  const partial = report.months.some((row) => row.partial);
  const monthChartWidth = points.length * 72 + 56;

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <Metric label={t("orders")} value={formatAmount(report.totals.orders)} hint={null} />
        <Metric label={t("revenue")} value={formatMoney(report.totals.revenue, "GEL")} hint={null} />
        <Metric label={t("averageCheck")} value={average} hint={null} />
        <Metric label={t("kilograms")} value={formatAmount(report.totals.kilograms)} hint={null} />
        <Metric label={t("monthsCount")} value={formatAmount(report.totals.months)} hint={since} />
      </div>
      {partial ? <Note>{t("partialNote")}</Note> : null}
      <Section title={t("byMonthOrders")}>
        <ChartFrame minWidth={monthChartWidth}>
          <BarChart data={points} margin={{ top: 24, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatAmount(Number(value))} />
            <Bar dataKey="orders" name={t("orders")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]}>
              {points.map((point) => (
                <Cell key={point.label} fillOpacity={point.partial ? 0.45 : 1} />
              ))}
              <LabelList
                dataKey="orders"
                content={(props) => (
                  <BarValueLabel viewBox={props.viewBox} value={props.value} format={ordersBarLabel} />
                )}
              />
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("byMonthRevenue")}>
        <ChartFrame minWidth={monthChartWidth}>
          <BarChart data={points} margin={{ top: 24, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatMoney(Number(value), "GEL")} />
            <Bar dataKey="revenue" name={t("revenue")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]}>
              {points.map((point) => (
                <Cell key={point.label} fillOpacity={point.partial ? 0.45 : 1} />
              ))}
              <LabelList
                dataKey="revenue"
                content={(props) => (
                  <BarValueLabel viewBox={props.viewBox} value={props.value} format={revenueBarLabel} />
                )}
              />
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("averageCheck")}>
        <ChartFrame>
          <LineChart data={linePoints(points, "average")} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatMoney(Number(value), "GEL")} />
            <Line
              type="monotone"
              dataKey="solid"
              name={t("averageCheck")}
              stroke={COLOR_ORDERS}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="dashed"
              name={t("averageCheck")}
              stroke={COLOR_ORDERS}
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 2 }}
              legendType="none"
              connectNulls
            />
          </LineChart>
        </ChartFrame>
      </Section>
      <Section title={t("kilogramsByMonth")}>
        <ChartFrame>
          <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatAmount(Number(value))} />
            <Bar dataKey="kilograms" name={t("kilograms")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]}>
              {points.map((point) => (
                <Cell key={point.label} fillOpacity={point.partial ? 0.45 : 1} />
              ))}
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("pricePerKg")}>
        <ChartFrame>
          <LineChart data={linePoints(points, "pricePerKg")} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatMoney(Number(value), "GEL")} />
            <Line
              type="monotone"
              dataKey="solid"
              name={t("pricePerKg")}
              stroke={COLOR_REVENUE}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="dashed"
              name={t("pricePerKg")}
              stroke={COLOR_REVENUE}
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 2 }}
              legendType="none"
              connectNulls
            />
          </LineChart>
        </ChartFrame>
      </Section>
      <Section title={t("channels")}>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={channelMetric === "revenue" ? "primary" : "outline"}
            onClick={() => setChannelMetric("revenue")}
          >
            {t("revenue")}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={channelMetric === "orders" ? "primary" : "outline"}
            onClick={() => setChannelMetric("orders")}
          >
            {t("orders")}
          </Button>
        </div>
        <ChartFrame>
          <BarChart data={channels} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval="preserveStartEnd" />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) =>
                channelMetric === "revenue" ? formatMoney(Number(value), "GEL") : formatAmount(Number(value))
              }
            />
            <Legend />
            <Bar dataKey="direct" name={t("channelDirect")} stackId="channel" fill={COLOR_NEW}>
              {channels.map((row) => (
                <Cell key={row.label} fillOpacity={row.partial ? 0.45 : 1} />
              ))}
            </Bar>
            <Bar dataKey="website" name={t("channelWebsite")} stackId="channel" fill={COLOR_ORDERS}>
              {channels.map((row) => (
                <Cell key={row.label} fillOpacity={row.partial ? 0.45 : 1} />
              ))}
            </Bar>
            <Bar dataKey="flowwow" name={t("channelFlowwow")} stackId="channel" fill={COLOR_REVENUE}>
              {channels.map((row) => (
                <Cell key={row.label} fillOpacity={row.partial ? 0.45 : 1} />
              ))}
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("paymentsTitle")}>
        <ChartFrame>
          <BarChart data={payments} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" horizontal={false} />
            <XAxis type="number" tick={AXIS_TICK} />
            <YAxis type="category" dataKey="label" tick={AXIS_TICK} width={168} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value) => formatMoney(Number(value), "GEL")} />
            <Bar dataKey="revenue" name={t("revenue")} fill={COLOR_REVENUE} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("monthly")}>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">{t("month")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("orders")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("revenue")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("averageCheck")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("kilograms")}</th>
                <th className="py-2 pr-3 text-right font-medium">{t("pricePerKg")}</th>
                <th className="py-2 text-right font-medium">{t("revenueChange")}</th>
              </tr>
            </thead>
            <tbody>
              {report.months.map((row, index) => {
                const previous = index === 0 ? null : report.months[index - 1].revenue;
                const change = previous === null ? t("emptyValue") : deltaText(row.revenue, previous, true);
                return (
                  <tr key={row.month} className="border-t border-[var(--line)]">
                    <td className="py-2 pr-3">
                      {monthLabel(row.month, locale)}
                      {row.partial ? (
                        <span className="mt-0.5 block text-xs text-[var(--muted)]">{t("partial")}</span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.orders)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.revenue, "GEL")}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {row.average_check === null ? t("emptyValue") : formatMoney(row.average_check, "GEL")}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{row.kilograms}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {row.price_per_kg === null ? t("emptyValue") : formatMoney(row.price_per_kg, "GEL")}
                    </td>
                    <td className="py-2 text-right tabular-nums">{change}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
