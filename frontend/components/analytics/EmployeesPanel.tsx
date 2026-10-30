"use client";

import { useLocale, useTranslations } from "next-intl";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Spinner } from "@/components/ui/spinner";
import { PIE_COLORS, REST_COLOR, SharePie } from "@/components/analytics/SharePie";
import {
  AXIS_TICK,
  COLOR_NEW,
  COLOR_ORDERS,
  COLOR_REVENUE,
  COLOR_USUAL,
  ChartFrame,
  Metric,
  Note,
  Section,
  TOOLTIP_STYLE,
  dayLabel,
  deltaText,
  monthLabel,
} from "@/components/analytics/widgets";
import { useAnalyticsEmployees } from "@/hooks/useAnalytics";
import { useFinancePeriod } from "@/hooks/useFinancePeriod";
import { formatAmount, formatMoney } from "@/lib/format";
import type { AnalyticsEmployees, AnalyticsProductKind } from "@/lib/api/types";

const WEEKDAYS = ["weekdayMon", "weekdayTue", "weekdayWed", "weekdayThu", "weekdayFri", "weekdaySat", "weekdaySun"] as const;

const KIND_LABELS: Record<AnalyticsProductKind, string> = {
  cake: "kindCake",
  bento: "kindBento",
  cupcake: "kindCupcake",
  macaron: "kindMacaron",
  addon: "kindAddon",
  other: "kindOther",
};

const KINDS = ["cake", "bento", "cupcake", "macaron", "addon", "other"] as const;

const SHIFT_ORIGIN = 7 * 60;
const SHIFT_SPAN = 15 * 60;

type ChartPoint = Record<string, string | number | null>;

function percentPoints(value: string | null): string | null {
  if (value === null) return null;
  return String(Math.round(Number(value) * 100));
}

function deltaHint(current: string | null, previous: string | null, money: boolean): string | null {
  if (current === null || previous === null) return null;
  return deltaText(current, previous, money);
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

function clockMinutes(value: string): number {
  const [hour, minute] = value.split(":");
  return Number(hour) * 60 + Number(minute);
}

function dayNumber(value: string): string {
  return String(Number(value.slice(8, 10)));
}

function bakerOrder(report: AnalyticsEmployees): { id: number; name: string }[] {
  const selected = report.employees
    .filter((row) => row.made > 0 || Number(row.made_kilograms) > 0)
    .sort(
      (left, right) =>
        Number(right.made_kilograms) - Number(left.made_kilograms) ||
        left.name.localeCompare(right.name) ||
        left.id - right.id,
    );
  const seen = new Set(selected.map((row) => row.id));
  const extra: { id: number; name: string }[] = [];
  for (const month of report.months) {
    for (const baker of month.bakers) {
      if (seen.has(baker.id)) continue;
      seen.add(baker.id);
      extra.push({ id: baker.id, name: baker.name });
    }
  }
  extra.sort((left, right) => left.name.localeCompare(right.name) || left.id - right.id);
  return [...selected.map((row) => ({ id: row.id, name: row.name })), ...extra];
}

function fillBakers(point: ChartPoint, bakers: { id: number }[], rows: { id: number; kilograms: string }[]) {
  for (const baker of bakers) {
    const found = rows.find((row) => row.id === baker.id);
    point[`b${baker.id}`] = found === undefined ? 0 : Number(found.kilograms);
  }
}

export function EmployeesPanel() {
  const t = useTranslations("analytics");
  const locale = useLocale();
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
  if (report.employees.length === 0 && report.months.length === 0) {
    return <Note>{t("employeesEmpty")}</Note>;
  }

  const partialLabel = t("partial");
  const bakers = bakerOrder(report);
  const share = percentPoints(report.totals.salary_share);
  const previousShare = percentPoints(report.previous.salary_share);
  const months = report.months.map((row) => {
    const point: ChartPoint = {
      label: row.partial ? `${monthLabel(row.month, locale)} · ${partialLabel}` : monthLabel(row.month, locale),
      hourly: Number(row.hourly_money),
      monthly: Number(row.monthly_money),
      share: row.salary_share === null ? null : Number(row.salary_share) * 100,
      perKg: row.money_per_kg === null ? null : Number(row.money_per_kg),
      perHour: row.kg_per_hour === null ? null : Number(row.kg_per_hour),
      unassigned: Number(row.unassigned_kilograms),
    };
    fillBakers(point, bakers, row.bakers);
    return point;
  });
  const days = report.days.map((row) => {
    const point: ChartPoint = {
      label: dayLabel(row.date, locale),
      hours: Number(row.hours),
      rate: row.kg_per_hour === null ? null : Number(row.kg_per_hour),
      unassigned: Number(row.unassigned_kilograms),
    };
    fillBakers(point, bakers, row.bakers);
    return point;
  });
  const rateMedian = median(days.flatMap((row) => (typeof row.rate === "number" ? [row.rate] : [])));
  const weekdays = report.weekdays.map((row) => ({
    label: t(WEEKDAYS[row.weekday]),
    hours: Number(row.hours),
    kilograms: Number(row.kilograms),
  }));
  const hourRows = report.employees
    .filter((row) => Number(row.hours) > 0)
    .sort((left, right) => Number(right.hours) - Number(left.hours) || left.name.localeCompare(right.name))
    .map((row) => ({ key: String(row.id), label: row.name, value: Number(row.hours) }));
  const kilogramRows = bakers
    .map((baker) => {
      const person = report.employees.find((row) => row.id === baker.id);
      return {
        key: String(baker.id),
        label: baker.name,
        value: person === undefined ? 0 : Number(person.made_kilograms),
      };
    })
    .filter((row) => row.value > 0);
  const shifts = report.employees.flatMap((row) =>
    row.arrival === null || row.departure === null
      ? []
      : [{ id: row.id, name: row.name, arrival: row.arrival, departure: row.departure }],
  );
  const kindRows = report.employees
    .filter((row) => row.kinds.length > 0)
    .map((row) => {
      const point: ChartPoint = { name: row.name };
      for (const kind of KINDS) {
        const found = row.kinds.find((item) => item.kind === kind);
        point[kind] = found === undefined ? 0 : found.quantity;
      }
      return point;
    });
  const production = report.employees.flatMap((row) =>
    row.production_minutes === null ? [] : [{ name: row.name, minutes: Number(row.production_minutes) }],
  );
  const monthWidth = Math.max(months.length, 1) * 72 + 56;
  const dayWidth = Math.max(days.length, 1) * 36 + 56;

  return (
    <div className="grid gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <Metric
          label={t("staffFund")}
          value={formatMoney(report.totals.money, "GEL")}
          hint={deltaHint(report.totals.money, report.previous.money, true)}
        />
        <Metric
          label={t("staffShare")}
          value={share === null ? t("emptyValue") : `${share}%`}
          hint={deltaHint(share, previousShare, false)}
        />
        <Metric
          label={t("staffPerKg")}
          value={report.totals.money_per_kg === null ? t("emptyValue") : formatMoney(report.totals.money_per_kg, "GEL")}
          hint={deltaHint(report.totals.money_per_kg, report.previous.money_per_kg, true)}
        />
        <Metric
          label={t("staffPerHour")}
          value={report.totals.kg_per_hour === null ? t("emptyValue") : formatAmount(report.totals.kg_per_hour)}
          hint={deltaHint(report.totals.kg_per_hour, report.previous.kg_per_hour, false)}
        />
        <Metric
          label={t("staffHoursShifts")}
          value={`${formatAmount(report.totals.hours)} · ${report.totals.shifts}`}
          hint={deltaHint(report.totals.hours, report.previous.hours, false)}
        />
      </div>
      <Note>
        {t("staffGaps", {
          baker: report.gaps.without_baker,
          shifts: report.gaps.unclosed_shifts,
          composition: report.gaps.without_composition,
          production: report.gaps.without_production,
        })}
      </Note>
      {months.length > 0 ? (
        <>
          <Section title={t("staffCost")}>
            <ChartFrame minWidth={monthWidth}>
              <ComposedChart data={months} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e8ddcd" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} />
                <YAxis yAxisId="money" tick={AXIS_TICK} width={48} />
                <YAxis yAxisId="share" orientation="right" tick={AXIS_TICK} width={36} unit="%" />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend />
                <Bar yAxisId="money" dataKey="hourly" name={t("staffHourly")} stackId="fund" fill={COLOR_ORDERS} />
                <Bar yAxisId="money" dataKey="monthly" name={t("staffMonthly")} stackId="fund" fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
                <Line yAxisId="share" dataKey="share" name={t("staffShare")} stroke={COLOR_NEW} strokeWidth={2} dot={false} connectNulls={false} />
              </ComposedChart>
            </ChartFrame>
          </Section>
          <Section title={t("staffRates")}>
            <ChartFrame minWidth={monthWidth}>
              <ComposedChart data={months} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e8ddcd" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} />
                <YAxis yAxisId="gel" tick={AXIS_TICK} width={48} />
                <YAxis yAxisId="kg" orientation="right" tick={AXIS_TICK} width={36} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend />
                <Line yAxisId="gel" dataKey="perKg" name={t("staffPerKg")} stroke={COLOR_REVENUE} strokeWidth={2} dot={false} connectNulls={false} />
                <Line yAxisId="kg" dataKey="perHour" name={t("staffPerHour")} stroke={COLOR_ORDERS} strokeWidth={2} dot={false} connectNulls={false} />
              </ComposedChart>
            </ChartFrame>
          </Section>
          <Section title={t("staffBakersMonths")}>
            <ChartFrame minWidth={monthWidth}>
              <BarChart data={months} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e8ddcd" vertical={false} />
                <XAxis dataKey="label" tick={AXIS_TICK} />
                <YAxis tick={AXIS_TICK} width={36} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend />
                {bakers.map((baker, index) => (
                  <Bar
                    key={baker.id}
                    dataKey={`b${baker.id}`}
                    name={baker.name}
                    stackId="kg"
                    fill={PIE_COLORS[index % PIE_COLORS.length]}
                  />
                ))}
                <Bar dataKey="unassigned" name={t("staffUnassigned")} stackId="kg" fill={REST_COLOR} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
          </Section>
        </>
      ) : null}
      <Section title={t("staffDays")}>
        <ChartFrame minWidth={dayWidth}>
          <ComposedChart data={days} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={16} />
            <YAxis yAxisId="kg" tick={AXIS_TICK} width={36} />
            <YAxis yAxisId="hours" orientation="right" tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend />
            {bakers.map((baker, index) => (
              <Bar
                key={baker.id}
                yAxisId="kg"
                dataKey={`b${baker.id}`}
                name={baker.name}
                stackId="kg"
                fill={PIE_COLORS[index % PIE_COLORS.length]}
              />
            ))}
            <Bar yAxisId="kg" dataKey="unassigned" name={t("staffUnassigned")} stackId="kg" fill={REST_COLOR} />
            <Line yAxisId="hours" dataKey="hours" name={t("hours")} stroke={COLOR_NEW} strokeWidth={2} dot={false} />
          </ComposedChart>
        </ChartFrame>
      </Section>
      <Section title={t("staffDayRate")}>
        <ChartFrame minWidth={dayWidth}>
          <ComposedChart data={days} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e8ddcd" vertical={false} />
            <XAxis dataKey="label" tick={AXIS_TICK} minTickGap={16} />
            <YAxis tick={AXIS_TICK} width={36} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Line dataKey="rate" name={t("staffPerHour")} stroke={COLOR_REVENUE} strokeWidth={2} dot={false} connectNulls={false} />
            {rateMedian === null ? null : (
              <ReferenceLine y={rateMedian} stroke={COLOR_USUAL} strokeDasharray="4 4" />
            )}
          </ComposedChart>
        </ChartFrame>
      </Section>
      <div className="grid gap-6 lg:grid-cols-2">
        <Section title={t("staffWeekKg")}>
          <ChartFrame>
            <BarChart data={weekdays} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e8ddcd" vertical={false} />
              <XAxis dataKey="label" tick={AXIS_TICK} />
              <YAxis tick={AXIS_TICK} width={36} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="kilograms" name={t("madeKilograms")} fill={COLOR_REVENUE} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartFrame>
        </Section>
        <Section title={t("staffWeekHours")}>
          <ChartFrame>
            <BarChart data={weekdays} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e8ddcd" vertical={false} />
              <XAxis dataKey="label" tick={AXIS_TICK} />
              <YAxis tick={AXIS_TICK} width={36} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="hours" name={t("hours")} fill={COLOR_ORDERS} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartFrame>
        </Section>
      </div>
      <Section title={t("staffHoursShare")}>
        {hourRows.length === 0 ? <Note>{t("emptyValue")}</Note> : <SharePie rows={hourRows} collapse={false} restLabel="" />}
      </Section>
      <Section title={t("staffShift")}>
        {shifts.length === 0 ? <Note>{t("emptyValue")}</Note> : <ShiftRows rows={shifts} />}
      </Section>
      <Section title={t("staffKgShare")}>
        {kilogramRows.length === 0 ? (
          <Note>{t("emptyValue")}</Note>
        ) : (
          <SharePie rows={kilogramRows} collapse={false} restLabel="" />
        )}
      </Section>
      <Section title={t("staffKinds")}>
        {kindRows.length === 0 ? (
          <Note>{t("emptyValue")}</Note>
        ) : (
          <ChartFrame>
            <BarChart data={kindRows} layout="vertical" margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="#e8ddcd" horizontal={false} />
              <XAxis type="number" tick={AXIS_TICK} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={AXIS_TICK} width={96} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend />
              {KINDS.map((kind, index) => (
                <Bar
                  key={kind}
                  dataKey={kind}
                  name={t(KIND_LABELS[kind])}
                  stackId="kinds"
                  fill={PIE_COLORS[index % PIE_COLORS.length]}
                />
              ))}
            </BarChart>
          </ChartFrame>
        )}
      </Section>
      <Section title={t("staffProduction")}>
        {production.length === 0 ? (
          <Note>{t("emptyValue")}</Note>
        ) : (
          <ChartFrame>
            <BarChart data={production} layout="vertical" margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <CartesianGrid stroke="#e8ddcd" horizontal={false} />
              <XAxis type="number" tick={AXIS_TICK} />
              <YAxis type="category" dataKey="name" tick={AXIS_TICK} width={96} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="minutes" name={t("staffProduction")} fill={COLOR_REVENUE} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ChartFrame>
        )}
      </Section>
      {report.timesheet.length > 0 ? (
        <Section title={t("staffTimesheet")}>
          <Timesheet report={report} />
        </Section>
      ) : null}
      <Section title={t("employees")}>
        {report.employees.length === 0 ? <Note>{t("employeesEmpty")}</Note> : <EmployeeTable report={report} />}
      </Section>
    </div>
  );
}

function ShiftRows({ rows }: { rows: { id: number; name: string; arrival: string; departure: string }[] }) {
  return (
    <div className="grid gap-2">
      <div className="grid grid-cols-[8rem_minmax(0,1fr)] gap-3 text-xs text-[var(--muted)]">
        <span />
        <span className="flex justify-between">
          <span>07:00</span>
          <span>22:00</span>
        </span>
      </div>
      {rows.map((row) => {
        const start = clockMinutes(row.arrival);
        const finish = clockMinutes(row.departure);
        const left = ((start - SHIFT_ORIGIN) / SHIFT_SPAN) * 100;
        const width = ((finish - start) / SHIFT_SPAN) * 100;
        const clampedLeft = Math.max(0, Math.min(100, left));
        const clampedWidth = Math.max(0, Math.min(100 - clampedLeft, width));
        return (
          <div key={row.id} className="grid grid-cols-[8rem_minmax(0,1fr)] items-center gap-3 text-sm">
            <span className="truncate font-medium text-[var(--ink)]">{row.name}</span>
            <div className="relative h-7 rounded-lg bg-[var(--cream)]">
              <div
                className="absolute top-1 bottom-1 rounded-md bg-[var(--brand)]"
                style={{ left: `${clampedLeft}%`, width: `${clampedWidth}%` }}
              />
              <span className="absolute inset-0 flex items-center justify-center text-xs tabular-nums text-[var(--ink)]">
                {row.arrival}–{row.departure}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Timesheet({ report }: { report: AnalyticsEmployees }) {
  const t = useTranslations("analytics");
  const header = report.timesheet[0];
  let max = 0;
  for (const row of report.timesheet) {
    for (const day of row.days) {
      const hours = Number(day.hours);
      if (hours > max) max = hours;
    }
  }
  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-1 text-sm">
        <thead>
          <tr>
            <th />
            {header.days.map((day) => (
              <th key={day.date} className="px-1 text-xs font-medium text-[var(--muted)]">
                {dayNumber(day.date)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {report.timesheet.map((row) => (
            <tr key={row.id}>
              <th className="whitespace-nowrap pr-3 text-left font-medium text-[var(--ink)]">{row.name}</th>
              {row.days.map((day) => {
                const hours = Number(day.hours);
                const filled = day.open || hours > 0;
                const alpha = max === 0 ? 0 : hours / max;
                return (
                  <td key={day.date}>
                    <span
                      className="flex min-h-10 min-w-8 items-center justify-center rounded-lg px-1 text-xs tabular-nums"
                      style={
                        day.open
                          ? { background: "rgba(179, 74, 58, 0.45)" }
                          : filled
                            ? { background: `rgba(91, 143, 168, ${Math.min(1, alpha)})` }
                            : { background: "var(--cream)" }
                      }
                    >
                      {day.open ? t("staffOpen") : hours > 0 ? formatAmount(day.hours) : ""}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
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
            <th className="py-2 pr-3 font-medium">{t("payType")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("staffShifts")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("hours")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("staffAverage")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("salary")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("staffMoneyShare")}</th>
            <th className="py-2 pr-3 text-right font-medium">{t("staffOrders")}</th>
            <th className="py-2 text-right font-medium">{t("madeKilograms")}</th>
          </tr>
        </thead>
        <tbody>
          {report.employees.map((row) => (
            <tr key={row.id} className="border-t border-[var(--line)]">
              <td className="py-2 pr-3 font-medium">{row.name}</td>
              <td className="py-2 pr-3">{row.monthly ? t("payMonthly") : t("payHourly")}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.shifts}</td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatAmount(row.hours)}</td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {row.average_shift === null ? t("emptyValue") : formatAmount(row.average_shift)}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">{formatMoney(row.money, "GEL")}</td>
              <td className="py-2 pr-3 text-right tabular-nums">
                {row.money_share === null ? t("emptyValue") : `${Math.round(Number(row.money_share) * 100)}%`}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums">{row.made}</td>
              <td className="py-2 text-right tabular-nums">{formatAmount(row.made_kilograms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
