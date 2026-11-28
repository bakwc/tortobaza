"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { CrmClientOrdersDialog } from "@/components/crm/CrmClientOrdersDialog";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsClients } from "@/hooks/useAnalytics";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsClients, AnalyticsCustomer } from "@/lib/api/types";
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
  monthLabel,
} from "@/components/analytics/widgets";

const SPAN_KEY = {
  7: "span7",
  14: "span14",
  30: "span30",
  60: "span60",
  90: "span90",
  180: "span180",
  365: "span365",
} as const;

type SpanDays = keyof typeof SPAN_KEY;

function returnShare(part: number, total: number): number | null {
  if (part === 0 || total === 0) return null;
  return Math.round((part / total) * 100);
}

function spanKey(days: number | null) {
  return days === null ? "spanOver" : SPAN_KEY[days as SpanDays];
}

function spanRows(bins: AnalyticsClients["gaps"]["bins"], label: (days: number | null) => string) {
  return bins.map((bin) => ({
    label: label(bin.days),
    share: Math.round(Number(bin.share) * 100),
    cumulative: Math.round(Number(bin.cumulative) * 100),
    count: bin.count,
  }));
}

type SpanRow = ReturnType<typeof spanRows>[number];

export function ClientsPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const query = useAnalyticsClients();

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
  const orders = report.months.map((row) => ({
    label: monthLabel(row.month, locale),
    newOrders: row.new_orders,
    returnOrders: row.return_orders,
    returnShare: returnShare(row.return_orders, row.new_orders + row.return_orders),
  }));
  const revenue = report.months.map((row) => {
    const newRevenue = Number(row.new_revenue);
    const returnRevenue = Number(row.return_revenue);
    return {
      label: monthLabel(row.month, locale),
      newRevenue,
      returnRevenue,
      returnShare: returnShare(returnRevenue, newRevenue + returnRevenue),
    };
  });
  const frequency = [
    { label: t("once"), clients: report.frequency.once.clients },
    { label: t("twice"), clients: report.frequency.twice.clients },
    { label: t("more"), clients: report.frequency.more.clients },
  ];
  const repeatHint =
    Number(report.known_revenue) === 0
      ? null
      : t("repeatRevenue", {
          share: Math.round((Number(report.repeat_revenue) / Number(report.known_revenue)) * 100),
        });
  const header = report.cohorts[0];

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label={t("clientsTitle")} value={formatAmount(report.clients)} hint={null} />
        <Metric label={t("repeatClients")} value={formatAmount(report.repeat_clients)} hint={repeatHint} />
        <Metric label={t("knownOrders")} value={formatAmount(report.known_orders)} hint={null} />
        <Metric label={t("unknownClients")} value={formatAmount(report.unknown_orders)} hint={null} />
      </div>
      <Note>{t("clientsNote", { count: report.unknown_orders })}</Note>
      <Section title={t("byMonthOrders")}>
        <ChartFrame>
          <BarChart data={orders} margin={{ top: 20, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            <Bar dataKey="newOrders" name={t("newClients")} stackId="orders" fill={COLOR_NEW} />
            <Bar dataKey="returnOrders" name={t("returning")} stackId="orders" fill={COLOR_REVENUE}>
              <LabelList dataKey="returnShare" position="top" fill="#666666" fontSize={12} formatter={(value) => (typeof value === "number" ? `${value}%` : "")} />
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("byMonthRevenue")}>
        <ChartFrame>
          <BarChart data={revenue} margin={{ top: 20, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={48} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            <Bar dataKey="newRevenue" name={t("newClients")} stackId="revenue" fill={COLOR_NEW} />
            <Bar dataKey="returnRevenue" name={t("returning")} stackId="revenue" fill={COLOR_REVENUE}>
              <LabelList dataKey="returnShare" position="top" fill="#666666" fontSize={12} formatter={(value) => (typeof value === "number" ? `${value}%` : "")} />
            </Bar>
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("cohorts")}>
        <Note>{t("cohortNote")}</Note>
        {header ? (
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-2 text-sm">
              <thead>
                <tr>
                  <th />
                  {header.cells.map((cell) => (
                    <th key={cell.offset} className="px-2 text-xs font-medium text-[var(--muted)]">
                      {t("cohortOffset", { offset: cell.offset })}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.cohorts.map((row) => (
                  <tr key={row.month}>
                    <th className="whitespace-nowrap pr-3 text-left font-medium text-[var(--ink)]">
                      {monthLabel(row.month, locale)}
                      <span className="mt-0.5 block text-xs font-normal text-[var(--muted)]">
                        {t("cohortClients", { count: row.clients })}
                      </span>
                    </th>
                    {row.cells.map((cell) => (
                      <td key={cell.offset}>
                        {cell.observed && cell.count !== null && cell.share !== null ? (
                          <span
                            className="flex min-h-12 min-w-16 flex-col items-center justify-center rounded-lg px-2 py-1"
                            style={{ background: `rgba(204, 118, 127, ${Math.min(1, Number(cell.share))})` }}
                          >
                            <b>{Math.round(Number(cell.share) * 100)}%</b>
                            <small>{cell.count}</small>
                          </span>
                        ) : (
                          <span className="flex min-h-12 min-w-16 items-center justify-center rounded-lg bg-[var(--cream)] text-[var(--muted)]">
                            {t("emptyValue")}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Note>{t("emptyValue")}</Note>
        )}
      </Section>
      <Section title={t("gap")}>
        {report.gaps.median === null ? (
          <Note>{t("gapEmpty")}</Note>
        ) : (
          <>
            <Note>{t("gapNote")}</Note>
            <Note>{t("gapMedian", { days: formatAmount(report.gaps.median) })}</Note>
            <SpanChart
              rows={spanRows(report.gaps.bins, (days) => t(spanKey(days)))}
              color={COLOR_REVENUE}
            />
          </>
        )}
      </Section>
      <Section title={t("tenure")}>
        {report.gaps.median === null ? (
          <Note>{t("gapEmpty")}</Note>
        ) : (
          <>
            <Note>{t("tenureNote")}</Note>
            <SpanChart
              rows={spanRows(report.tenure.bins, (days) => t(spanKey(days)))}
              color={COLOR_ORDERS}
            />
          </>
        )}
      </Section>
      <Section title={t("frequency")}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Metric
            label={t("once")}
            value={formatAmount(report.frequency.once.clients)}
            hint={formatMoney(report.frequency.once.revenue, "GEL")}
          />
          <Metric
            label={t("twice")}
            value={formatAmount(report.frequency.twice.clients)}
            hint={formatMoney(report.frequency.twice.revenue, "GEL")}
          />
          <Metric
            label={t("more")}
            value={formatAmount(report.frequency.more.clients)}
            hint={formatMoney(report.frequency.more.revenue, "GEL")}
          />
        </div>
        <ChartFrame>
          <BarChart data={frequency} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} />
            <YAxis tick={AXIS_TICK} width={36} allowDecimals={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="clients" name={t("clientsTitle")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Section>
      <Section title={t("topRepeat")}>
        <h3 className="text-sm font-medium text-[var(--muted)]">{t("topRevenue")}</h3>
        <CustomerTable rows={report.top_revenue} />
        <h3 className="text-sm font-medium text-[var(--muted)]">{t("topOrders")}</h3>
        <CustomerTable rows={report.top_orders} />
      </Section>
    </div>
  );
}

function SpanChart({
  rows,
  color,
}: {
  rows: SpanRow[];
  color: string;
}) {
  const t = useTranslations("analytics");
  return (
    <ChartFrame>
      <BarChart data={rows} margin={{ top: 20, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#e8ddcd" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} />
        <YAxis tick={AXIS_TICK} width={48} domain={[0, 100]} tickFormatter={(value: number) => `${value}%`} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value, _name, item) => [`${value}% · ${item.payload.count}`, t("clientsTitle")]}
        />
        <Bar dataKey="share" name={t("clientsTitle")} fill={color} radius={[4, 4, 0, 0]}>
          <LabelList
            dataKey="share"
            content={(props) => <SpanLabel x={props.x} y={props.y} width={props.width} row={rows[Number(props.index)]} />}
          />
        </Bar>
      </BarChart>
    </ChartFrame>
  );
}

function SpanLabel({
  x,
  y,
  width,
  row,
}: {
  x?: number | string;
  y?: number | string;
  width?: number | string;
  row: SpanRow;
}) {
  return (
    <text x={Number(x) + Number(width) / 2} y={Number(y) - 8} fill="#666666" fontSize={12} textAnchor="middle">
      {`${row.share}%`}
      <tspan fontSize={10} dx={3}>{`(${row.cumulative}%)`}</tspan>
    </text>
  );
}

function CustomerTable({ rows }: { rows: AnalyticsCustomer[] }) {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const [selected, setSelected] = useState<AnalyticsCustomer | null>(null);
  if (rows.length === 0) return <Note>{t("emptyValue")}</Note>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="py-2 pr-3 font-medium">{t("name")}</th>
            <th className="py-2 pr-3 font-medium">{t("phone")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("orders")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("revenue")}</th>
            <th className="py-2 pr-3 font-medium">{t("first")}</th>
            <th className="py-2 font-medium">{t("last")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.order_id} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3">
                <button
                  type="button"
                  onClick={() => setSelected(row)}
                  className="cursor-pointer font-medium text-[var(--brand)]"
                >
                  {row.name === "" ? t("emptyValue") : row.name}
                </button>
              </td>
              <td className="py-2 pr-3 tabular-nums">{row.phones.join(", ")}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.orders}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.revenue, "GEL")}</td>
              <td className="py-2 pr-3">{dayLabel(row.first, locale)}</td>
              <td className="py-2">{dayLabel(row.last, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected !== null ? (
        <CrmClientOrdersDialog
          orderId={selected.order_id}
          count={selected.orders}
          open
          onOpenChange={(open) => {
            if (!open) setSelected(null);
          }}
        />
      ) : null}
    </div>
  );
}
