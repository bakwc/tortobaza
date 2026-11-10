"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyticsPace } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsPace } from "@/lib/api/types";
import {
  AXIS_TICK,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  deltaText,
  monthLabel,
} from "@/components/analytics/widgets";

type PaceMonth = AnalyticsPace["months"][number];
type PaceKey = "revenue" | "orders" | "repeat_orders" | "created_orders" | "flowwow" | "website" | "direct";
type Channel = "flowwow" | "website" | "direct";

type PacePoint = {
  day: number;
  m0: number | null;
  m1: number | null;
  m2: number | null;
};

const SERIES = [
  { key: "m0", color: "#1f1a17", width: 2.5, opacity: 1, dash: "" },
  { key: "m1", color: "#cc767f", width: 2, opacity: 0.8, dash: "" },
  { key: "m2", color: "#5b8fa8", width: 2, opacity: 0.8, dash: "5 4" },
] as const;

const CHANNELS: { channel: Channel; label: "channelFlowwow" | "channelWebsite" | "channelDirect" }[] = [
  { channel: "flowwow", label: "channelFlowwow" },
  { channel: "website", label: "channelWebsite" },
  { channel: "direct", label: "channelDirect" },
];

function lastDay(month: PaceMonth): number {
  if (month.days.length === 0) return 0;
  return month.days[month.days.length - 1].day;
}

function paceAt(month: PaceMonth, day: number, key: PaceKey): number {
  if (day < 1 || month.days.length === 0) return 0;
  const capped = Math.min(day, lastDay(month));
  const value = month.days[capped - 1][key];
  return typeof value === "number" ? value : Number(value);
}

function dayValue(month: PaceMonth, day: number, key: PaceKey): number | null {
  if (day > lastDay(month)) return null;
  return paceAt(month, day, key);
}

function paceRows(months: PaceMonth[], key: PaceKey): PacePoint[] {
  const maxDay = months.reduce((max, month) => Math.max(max, lastDay(month)), 0);
  const rows: PacePoint[] = [];
  for (let day = 1; day <= maxDay; day += 1) {
    rows.push({
      day,
      m0: dayValue(months[0], day, key),
      m1: dayValue(months[1], day, key),
      m2: dayValue(months[2], day, key),
    });
  }
  return rows;
}

function compareHint(months: PaceMonth[], key: PaceKey, money: boolean, locale: string): string | null {
  const day = lastDay(months[0]);
  if (day === 0) return null;
  const current = paceAt(months[0], day, key);
  return months
    .slice(1)
    .map((month) => `${monthLabel(month.month, locale)} ${deltaText(current, paceAt(month, day, key), money)}`)
    .join(" · ");
}

function PaceChart({ rows, names, money }: { rows: PacePoint[]; names: string[]; money: boolean }) {
  return (
    <ChartFrame>
      <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#e8ddcd" vertical={false} />
        <XAxis dataKey="day" tick={AXIS_TICK} />
        <YAxis tick={AXIS_TICK} width={money ? 48 : 36} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value) => (money ? formatMoney(Number(value), "GEL") : formatAmount(Number(value)))}
        />
        <Legend />
        {SERIES.map((series, index) => (
          <Line
            key={series.key}
            type="monotone"
            dataKey={series.key}
            name={names[index]}
            stroke={series.color}
            strokeWidth={series.width}
            strokeOpacity={series.opacity}
            strokeDasharray={series.dash || undefined}
            dot={false}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ChartFrame>
  );
}

export function PacePanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const period = useFinancePeriod();
  const query = useAnalyticsPace(period.month);
  const [channel, setChannel] = useState<Channel>("flowwow");

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

  const months = query.data.months;
  const names = months.map((month) => monthLabel(month.month, locale));
  const day = lastDay(months[0]);

  return (
    <div className="grid gap-6">
      <Note>{t("asOfDay", { day })}</Note>
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric
          label={t("revenue")}
          value={formatMoney(paceAt(months[0], day, "revenue"), "GEL")}
          hint={compareHint(months, "revenue", true, locale)}
        />
        <Metric
          label={t("orders")}
          value={formatAmount(paceAt(months[0], day, "orders"))}
          hint={compareHint(months, "orders", false, locale)}
        />
        <Metric
          label={t("repeatOrders")}
          value={formatAmount(paceAt(months[0], day, "repeat_orders"))}
          hint={compareHint(months, "repeat_orders", false, locale)}
        />
      </div>
      <Section title={t("cumulativeRevenue")}>
        <PaceChart rows={paceRows(months, "revenue")} names={names} money />
      </Section>
      <Section title={t("cumulativeOrders")}>
        <PaceChart rows={paceRows(months, "orders")} names={names} money={false} />
      </Section>
      <Section title={t("createdOrders")}>
        <PaceChart rows={paceRows(months, "created_orders")} names={names} money={false} />
      </Section>
      <Section title={t("cumulativeRepeat")}>
        <PaceChart rows={paceRows(months, "repeat_orders")} names={names} money={false} />
      </Section>
      <Section title={t("channels")}>
        <div className="flex flex-wrap gap-2">
          {CHANNELS.map((item) => (
            <Button
              key={item.channel}
              type="button"
              size="sm"
              variant={channel === item.channel ? "primary" : "outline"}
              onClick={() => setChannel(item.channel)}
            >
              {t(item.label)}
            </Button>
          ))}
        </div>
        <PaceChart rows={paceRows(months, channel)} names={names} money />
      </Section>
    </div>
  );
}
