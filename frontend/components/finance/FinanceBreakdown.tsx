"use client";

import { useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import type { FinanceTransaction } from "@/lib/api/types";
import { formatAed, toGel } from "@/lib/format";
import { cn } from "@/lib/utils";

const INCOME_TYPES = ["online", "terminal", "cash", "transfer"] as const;
const EXPENSE_TYPES = ["salary", "rent", "products", "consumables", "equipment", "fees", "taxi", "gasoline", "marketing", "training"] as const;
const NEUTRAL_ACTIVE = "bg-[var(--ink)] text-white";
const INCOME_ACTIVE = "bg-emerald-600 text-white";
const EXPENSE_ACTIVE = "bg-rose-600 text-white";
const DONUT_SIZE = 260;
const DONUT_CENTER = 130;
const DONUT_OUTER = 118;
const DONUT_INNER = 70;
const DONUT_PULL = 8;
const DONUT_TOP = 7;
const REST_KEY = "__rest__";
const REST_COLOR = "#b5b5b5";
const PIE_COLORS = [
  "#cc767f",
  "#d4a017",
  "#5b8fa8",
  "#6a9a6a",
  "#8b6bb1",
  "#d07a3a",
  "#3d8b8b",
  "#7a7a7a",
  "#c45c8a",
  "#8fa83d",
  "#4f6db5",
  "#c47a5a",
  "#6b8f71",
  "#a67c52",
  "#7d6b8a",
  "#b85c5c",
  "#5c7a99",
  "#9a8b4f",
  "#6e6e8a",
  "#b56b7a",
  "#4f8f7a",
];

function isIncomeType(value: string): value is (typeof INCOME_TYPES)[number] {
  return INCOME_TYPES.some((item) => item === value);
}

function isExpenseType(value: string): value is (typeof EXPENSE_TYPES)[number] {
  return EXPENSE_TYPES.some((item) => item === value);
}

function readAccountIds(values: string[]): number[] {
  const ids: number[] = [];
  for (const value of values) {
    const id = Number(value);
    if (Number.isInteger(id)) ids.push(id);
  }
  return ids;
}

function toggleValue<T>(current: readonly T[], value: T): T[] {
  if (current.includes(value)) return current.filter((item) => item !== value);
  return [...current, value];
}

function hrefWithParams(
  pathname: string,
  current: string,
  updates: { key: string; values: string[] }[],
): string {
  const params = new URLSearchParams(current);
  for (const update of updates) {
    params.delete(update.key);
    for (const value of update.values) {
      params.append(update.key, value);
    }
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function monthDays(yyyyMm: string): string[] {
  const [yearStr, monthStr] = yyyyMm.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const count = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const days: string[] = [];
  for (let day = 1; day <= count; day += 1) {
    days.push(`${yyyyMm}-${String(day).padStart(2, "0")}`);
  }
  return days;
}

function magnitude(tx: FinanceTransaction, rates: Record<string, string>): number {
  return Math.abs(toGel(tx.amount, tx.account.currency, rates));
}

export function FinanceBreakdown({
  transactions,
  month,
  typeField,
  rates,
}: {
  transactions: FinanceTransaction[];
  month: string;
  typeField: "income_type" | "expense_type";
  rates: Record<string, string>;
}) {
  const t = useTranslations("finance");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const typeParam = typeField === "income_type" ? "income_type" : "expense_type";
  const accountFilters = readAccountIds(searchParams.getAll("account"));
  const typeFilters = searchParams.getAll(typeParam);
  const typeActiveClass = typeField === "income_type" ? INCOME_ACTIVE : EXPENSE_ACTIVE;

  function replaceFilters(next: { account: number[]; type: string[] }) {
    router.replace(
      hrefWithParams(pathname, searchParams.toString(), [
        { key: "account", values: next.account.map(String) },
        { key: typeParam, values: next.type },
      ]),
      { scroll: false },
    );
  }

  function openCounterparty(counterparty: string) {
    router.push(
      hrefWithParams("/finance", searchParams.toString(), [
        { key: "kind", values: [typeField === "income_type" ? "income" : "expense"] },
        { key: "counterparty", values: [counterparty] },
      ]),
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
        {t("empty")}
      </div>
    );
  }

  const knownTypes = typeField === "income_type" ? INCOME_TYPES : EXPENSE_TYPES;
  const accounts = [
    ...new Map(transactions.map((tx) => [tx.account.id, tx.account.name])).entries(),
  ].sort((left, right) => left[1].localeCompare(right[1]));
  const types = knownTypes.filter((type) => transactions.some((tx) => tx[typeField] === type));
  const hasUnspecified = transactions.some((tx) => tx[typeField] === "");
  const visible = transactions.filter(
    (tx) =>
      (accountFilters.length === 0 || accountFilters.includes(tx.account.id)) &&
      (typeFilters.length === 0 || typeFilters.includes(tx[typeField])),
  );

  const total = visible.reduce((sum, tx) => sum + magnitude(tx, rates), 0);
  const byAccount = group(visible, (tx) => String(tx.account.id), rates).map((row) => ({
    key: row.key,
    label: visible.find((tx) => String(tx.account.id) === row.key)?.account.name ?? row.key,
    amount: row.amount,
  }));
  const byType = group(visible, (tx) => tx[typeField], rates).map((row) => ({
    key: row.key,
    label: typeLabel(typeField, row.key, t),
    amount: row.amount,
  }));
  const counterparties = group(visible, (tx) => tx.counterparty_name || "unspecified", rates);
  const otherAmount = counterparties.slice(20).reduce((sum, row) => sum + row.amount, 0);
  const byCounterparty = counterparties.slice(0, 20).map((row) => ({
    key: row.key,
    label: row.key === "unspecified" ? t("unspecifiedCounterparty") : row.key,
    amount: row.amount,
  }));
  if (otherAmount > 0) {
    byCounterparty.push({
      key: "other",
      label: t("otherCounterparties"),
      amount: otherAmount,
    });
  }
  const byDay = monthDays(month).map((day) => ({
    date: day,
    amount: visible
      .filter((tx) => tx.date === day)
      .reduce((sum, tx) => sum + magnitude(tx, rates), 0),
  }));

  const showDonut = typeField === "expense_type";

  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4">
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-2xl border border-[var(--line)] bg-white px-3 py-2.5 shadow-sm">
        <FilterRow label={t("filterAccount")}>
          <FilterPill
            active={accountFilters.length === 0}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ account: [], type: typeFilters })}
          >
            {t("filterAll")}
          </FilterPill>
          {accounts.map(([id, name]) => (
            <FilterPill
              key={id}
              active={accountFilters.includes(id)}
              activeClass={NEUTRAL_ACTIVE}
              onClick={() => replaceFilters({ account: toggleValue(accountFilters, id), type: typeFilters })}
            >
              {name}
            </FilterPill>
          ))}
        </FilterRow>
        <FilterRow label={t(typeField === "income_type" ? "filterIncomeType" : "filterExpenseType")}>
          <FilterPill
            active={typeFilters.length === 0}
            activeClass={NEUTRAL_ACTIVE}
            onClick={() => replaceFilters({ account: accountFilters, type: [] })}
          >
            {t("filterAll")}
          </FilterPill>
          {types.map((type) => (
            <FilterPill
              key={type}
              active={typeFilters.includes(type)}
              activeClass={typeActiveClass}
              onClick={() => replaceFilters({ account: accountFilters, type: toggleValue(typeFilters, type) })}
            >
              {typeField === "income_type" ? t(`incomeTypes.${type}`) : t(`expenseTypes.${type}`)}
            </FilterPill>
          ))}
          {hasUnspecified ? (
            <FilterPill
              active={typeFilters.includes("")}
              activeClass={typeActiveClass}
              onClick={() => replaceFilters({ account: accountFilters, type: toggleValue(typeFilters, "") })}
            >
              {t("unspecified")}
            </FilterPill>
          ) : null}
        </FilterRow>
      </div>
      {visible.length === 0 ? (
        <div className="rounded-3xl border border-[var(--line)] bg-white p-8 text-center text-sm text-[var(--muted-2)] shadow-sm">
          {t("empty")}
        </div>
      ) : (
        <>
          <section className="min-w-0 rounded-3xl border border-[var(--line)] bg-white p-6 shadow-sm">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">
              {t("total")}
            </h2>
            <p className="mt-2 text-3xl font-semibold text-[var(--ink)]">{formatAed(total)}</p>
          </section>
          <ChartCard title={t("byAccount")}>
            <BreakdownChart
              rows={byAccount}
              selectedKeys={accountFilters.map(String)}
              disabledKeys={[]}
              onSelect={(key) =>
                replaceFilters({
                  account: accountFilters.includes(Number(key)) ? [] : [Number(key)],
                  type: typeFilters,
                })
              }
              showDonut={showDonut}
              collapseDonut={false}
              restLabel=""
            />
          </ChartCard>
          <ChartCard title={t("byType")}>
            <BreakdownChart
              rows={byType}
              selectedKeys={typeFilters}
              disabledKeys={[]}
              onSelect={(key) =>
                replaceFilters({
                  account: accountFilters,
                  type: typeFilters.includes(key) ? [] : [key],
                })
              }
              showDonut={showDonut}
              collapseDonut={false}
              restLabel=""
            />
          </ChartCard>
          <ChartCard title={t("byCounterparty")}>
            <BreakdownChart
              rows={byCounterparty}
              selectedKeys={[]}
              disabledKeys={["unspecified", "other"]}
              onSelect={openCounterparty}
              showDonut={showDonut}
              collapseDonut={showDonut}
              restLabel={t("otherCounterparties")}
            />
          </ChartCard>
          <ChartCard title={t("byDay")}>
            <DayColumns days={byDay} />
          </ChartCard>
        </>
      )}
    </div>
  );
}

function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
      <span className="mr-1 shrink-0 basis-full text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-2)] sm:basis-auto sm:w-28">
        {label}
      </span>
      {children}
    </div>
  );
}

function FilterPill({
  active,
  activeClass,
  onClick,
  children,
}: {
  active: boolean;
  activeClass: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors [&_svg]:h-3 [&_svg]:w-3",
        active
          ? cn("border-transparent", activeClass)
          : "border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--cream-soft)]",
      )}
    >
      {children}
    </button>
  );
}

type BreakdownRow = { key: string; label: string; amount: number };

type DrawnSlice = BreakdownRow & {
  color: string;
  percent: number;
  path: string;
  labelX: number;
  labelY: number;
  pullX: number;
  pullY: number;
  selectable: boolean;
};

function BreakdownChart({
  rows,
  selectedKeys,
  disabledKeys,
  onSelect,
  showDonut,
  collapseDonut,
  restLabel,
}: {
  rows: BreakdownRow[];
  selectedKeys: string[];
  disabledKeys: string[];
  onSelect: ((key: string) => void) | null;
  showDonut: boolean;
  collapseDonut: boolean;
  restLabel: string;
}) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const total = rows.reduce((sum, row) => sum + row.amount, 0);
  const percents = total === 0 ? rows.map(() => 0) : percentShares(rows.map((row) => row.amount), total);
  const max = Math.max(...rows.map((row) => row.amount));
  const collapseTail = collapseDonut && rows.length > DONUT_TOP;
  const slices = showDonut ? drawSlices(donutRows(rows, collapseTail, restLabel), disabledKeys, onSelect) : [];
  const focus = centerFocus(hoveredKey, rows, slices);
  const hasDonut = slices.length > 0;

  return (
    <div
      className={cn(
        "grid min-w-0 grid-cols-[minmax(0,1fr)] items-center gap-6",
        hasDonut && "md:grid-cols-[260px_minmax(0,1fr)]",
      )}
      onMouseLeave={() => setHoveredKey(null)}
    >
      {hasDonut ? (
        <svg viewBox={`0 0 ${DONUT_SIZE} ${DONUT_SIZE}`} className="mx-auto h-auto w-full max-w-[260px] font-sans">
          {slices.map((slice) => {
            const selected = selectedKeys.includes(slice.key);
            const hovered = sliceIsHovered(slice.key, hoveredKey, rows, collapseTail);
            const dimmed = sliceDimmed(hovered, selected, hoveredKey, selectedKeys);
            return (
              <g
                key={slice.key}
                transform={selected ? `translate(${slice.pullX} ${slice.pullY})` : undefined}
                onMouseEnter={() => setHoveredKey(slice.key)}
                onClick={slice.selectable && onSelect ? () => onSelect(slice.key) : undefined}
                className={slice.selectable ? "cursor-pointer" : undefined}
              >
                <path
                  d={slice.path}
                  fill={slice.color}
                  stroke="white"
                  strokeWidth={2}
                  strokeLinejoin="round"
                  fillRule="evenodd"
                  className="transition-[fill-opacity] duration-150"
                  style={{ fillOpacity: dimmed ? 0.4 : 1 }}
                />
                {slice.percent >= 5 ? (
                  <text
                    x={slice.labelX}
                    y={slice.labelY}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fill="#ffffff"
                    fontSize={12}
                    fontWeight={700}
                    pointerEvents="none"
                    className="transition-opacity duration-150"
                    style={{ textShadow: "0 1px 2px rgba(0,0,0,0.4)", opacity: dimmed ? 0.4 : 1 }}
                  >
                    {slice.percent}%
                  </text>
                ) : null}
              </g>
            );
          })}
          <g pointerEvents="none">
            {focus ? (
              <>
                <text
                  x={DONUT_CENTER}
                  y={DONUT_CENTER - 11}
                  textAnchor="middle"
                  className="fill-[var(--muted)]"
                  fontSize={11}
                >
                  {shortLabel(focus.label)}
                </text>
                <text
                  x={DONUT_CENTER}
                  y={DONUT_CENTER + 12}
                  textAnchor="middle"
                  className="fill-[var(--ink)]"
                  fontSize={centerAmountSize(focus.amount)}
                  fontWeight={600}
                >
                  {formatAed(focus.amount)}
                </text>
              </>
            ) : (
              <text
                x={DONUT_CENTER}
                y={DONUT_CENTER}
                textAnchor="middle"
                dominantBaseline="central"
                className="fill-[var(--ink)]"
                fontSize={centerAmountSize(total)}
                fontWeight={600}
              >
                {formatAed(total)}
              </text>
            )}
          </g>
        </svg>
      ) : null}
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        {rows.map((row, index) => {
          const active = selectedKeys.includes(row.key);
          const highlighted = rowHighlighted(row.key, index, hoveredKey, collapseTail);
          const color = rowColor(index, collapseTail);
          const content = (
            <>
              <div className="flex min-w-0 items-baseline justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                  <span
                    className={cn(
                      "min-w-0 truncate",
                      active ? "font-semibold text-[var(--brand)]" : "text-[var(--ink)]",
                    )}
                  >
                    {row.label}
                  </span>
                </span>
                <span className="flex shrink-0 items-baseline gap-2 tabular-nums">
                  <span className={cn("font-medium", active ? "text-[var(--brand)]" : "text-[var(--ink)]")}>
                    {formatAed(row.amount)}
                  </span>
                  <span className="w-11 text-right text-[var(--muted-2)]">{percents[index]}%</span>
                </span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-[var(--line)]">
                <div
                  className="h-1.5 rounded-full transition-[width]"
                  style={{
                    width: max === 0 ? "0%" : `${(row.amount / max) * 100}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
            </>
          );
          if (onSelect && !disabledKeys.includes(row.key)) {
            return (
              <button
                key={row.key}
                type="button"
                aria-pressed={active}
                onMouseEnter={() => setHoveredKey(row.key)}
                onClick={() => onSelect(row.key)}
                className={cn(
                  "w-full min-w-0 rounded-lg px-1.5 py-1 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--brand)]",
                  highlighted && "bg-[var(--cream-soft)]",
                )}
              >
                {content}
              </button>
            );
          }
          return (
            <div
              key={row.key}
              onMouseEnter={() => setHoveredKey(row.key)}
              className={cn("min-w-0 rounded-lg px-1.5 py-1", highlighted && "bg-[var(--cream-soft)]")}
            >
              {content}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function donutRows(rows: BreakdownRow[], collapseTail: boolean, restLabel: string): (BreakdownRow & { color: string })[] {
  const colored = rows.map((row, index) => ({ ...row, color: rowColor(index, false) }));
  if (!collapseTail) return colored;
  const head = colored.slice(0, DONUT_TOP);
  const amount = rows.slice(DONUT_TOP).reduce((sum, row) => sum + row.amount, 0);
  return [...head, { key: REST_KEY, label: restLabel, amount, color: REST_COLOR }];
}

function rowColor(index: number, collapseTail: boolean): string {
  if (collapseTail && index >= DONUT_TOP) return REST_COLOR;
  return PIE_COLORS[index % PIE_COLORS.length];
}

function drawSlices(
  slices: (BreakdownRow & { color: string })[],
  disabledKeys: string[],
  onSelect: ((key: string) => void) | null,
): DrawnSlice[] {
  const positive = slices.filter((slice) => slice.amount > 0);
  const total = positive.reduce((sum, slice) => sum + slice.amount, 0);
  if (total === 0) return [];
  const percents = percentShares(
    positive.map((slice) => slice.amount),
    total,
  );
  let angle = -Math.PI / 2;
  return positive.map((slice, index) => {
    const sweep = (slice.amount / total) * Math.PI * 2;
    const start = angle;
    const end = angle + sweep;
    angle = end;
    const mid = start + sweep / 2;
    const labelAt = polar(DONUT_CENTER, DONUT_CENTER, (DONUT_OUTER + DONUT_INNER) / 2, mid);
    return {
      key: slice.key,
      label: slice.label,
      amount: slice.amount,
      color: slice.color,
      percent: percents[index],
      path: pieSlice(DONUT_CENTER, DONUT_CENTER, DONUT_OUTER, DONUT_INNER, start, end),
      labelX: labelAt.x,
      labelY: labelAt.y,
      pullX: Math.cos(mid) * DONUT_PULL,
      pullY: Math.sin(mid) * DONUT_PULL,
      selectable: onSelect !== null && slice.key !== REST_KEY && !disabledKeys.includes(slice.key),
    };
  });
}

function centerFocus(
  hoveredKey: string | null,
  rows: BreakdownRow[],
  slices: DrawnSlice[],
): BreakdownRow | null {
  if (hoveredKey === null) return null;
  return rows.find((row) => row.key === hoveredKey) ?? slices.find((slice) => slice.key === hoveredKey) ?? null;
}

function sliceIsHovered(sliceKey: string, hoveredKey: string | null, rows: BreakdownRow[], collapseTail: boolean): boolean {
  if (hoveredKey === null) return false;
  if (sliceKey === hoveredKey) return true;
  if (!collapseTail || sliceKey !== REST_KEY) return false;
  const index = rows.findIndex((row) => row.key === hoveredKey);
  return index >= DONUT_TOP;
}

function sliceDimmed(hovered: boolean, selected: boolean, hoveredKey: string | null, selectedKeys: string[]): boolean {
  if (hoveredKey === null && selectedKeys.length === 0) return false;
  return !hovered && !selected;
}

function rowHighlighted(key: string, index: number, hoveredKey: string | null, collapseTail: boolean): boolean {
  if (hoveredKey === null) return false;
  if (hoveredKey === key) return true;
  return collapseTail && hoveredKey === REST_KEY && index >= DONUT_TOP;
}

function shortLabel(label: string): string {
  const limit = 14;
  if (label.length <= limit) return label;
  return `${label.slice(0, limit - 1)}…`;
}

function centerAmountSize(amount: number): number {
  const length = formatAed(amount).length;
  if (length > 16) return 11;
  if (length > 13) return 13;
  return 16;
}

function percentShares(amounts: number[], total: number): number[] {
  const exact = amounts.map((amount) => (amount / total) * 100);
  const percents = exact.map((value) => Math.floor(value));
  let leftover = 100 - percents.reduce((sum, value) => sum + value, 0);
  const order = exact
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((left, right) => right.remainder - left.remainder);
  for (const item of order) {
    if (leftover <= 0) break;
    percents[item.index] += 1;
    leftover -= 1;
  }
  return percents;
}

function pieSlice(cx: number, cy: number, outer: number, inner: number, start: number, end: number): string {
  if (end - start >= Math.PI * 2 - 1e-6) {
    return [
      `M ${cx} ${cy - outer}`,
      `A ${outer} ${outer} 0 1 1 ${cx} ${cy + outer}`,
      `A ${outer} ${outer} 0 1 1 ${cx} ${cy - outer}`,
      `M ${cx} ${cy - inner}`,
      `A ${inner} ${inner} 0 1 0 ${cx} ${cy + inner}`,
      `A ${inner} ${inner} 0 1 0 ${cx} ${cy - inner}`,
      "Z",
    ].join(" ");
  }
  const large = end - start > Math.PI ? 1 : 0;
  const outerStart = polar(cx, cy, outer, start);
  const outerEnd = polar(cx, cy, outer, end);
  const innerEnd = polar(cx, cy, inner, end);
  const innerStart = polar(cx, cy, inner, start);
  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outer} ${outer} 0 ${large} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${inner} ${inner} 0 ${large} 0 ${innerStart.x} ${innerStart.y}`,
    "Z",
  ].join(" ");
}

function polar(cx: number, cy: number, radius: number, angle: number): { x: number; y: number } {
  return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-3xl border border-[var(--line)] bg-white p-4 shadow-sm sm:p-6">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--ink)]/60">{title}</h2>
      <div className="mt-4 min-w-0">{children}</div>
    </section>
  );
}

function DayColumns({ days }: { days: { date: string; amount: number }[] }) {
  const max = Math.max(...days.map((day) => day.amount));
  const lastDay = Number(days[days.length - 1].date.slice(8));
  return (
    <div className="min-w-0">
      <p className="mb-2 text-left text-[10px] text-[var(--muted-2)]">{formatAed(max)}</p>
      <div className="flex w-full min-w-0 items-end gap-0.5 sm:gap-1">
        {days.map((day) => {
          const dayNum = Number(day.date.slice(8));
          const height = day.amount === 0 || max === 0 ? 0 : Math.max(4, (day.amount / max) * 112);
          const showNumber = mobileDayLabel(dayNum, lastDay);
          return (
            <div key={day.date} title={formatAed(day.amount)} className="flex min-w-0 flex-1 flex-col items-center gap-1">
              <div className="flex h-28 w-full items-end rounded-t bg-[var(--cream)]">
                <div className="w-full rounded-t bg-[var(--brand)]" style={{ height }} />
              </div>
              <span className="relative block h-3 w-full">
                <span
                  className={cn(
                    "absolute left-1/2 top-0 -translate-x-1/2 whitespace-nowrap text-[10px] leading-none text-[var(--muted-2)]",
                    showNumber ? "block" : "hidden sm:block",
                  )}
                >
                  {dayNum}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function mobileDayLabel(day: number, lastDay: number): boolean {
  return day === lastDay || day === 1 || day === 5 || day === 10 || day === 15 || day === 20 || day === 25;
}

function group(
  transactions: FinanceTransaction[],
  keyOf: (tx: FinanceTransaction) => string,
  rates: Record<string, string>,
): { key: string; amount: number }[] {
  const totals = new Map<string, number>();
  for (const tx of transactions) {
    const key = keyOf(tx);
    totals.set(key, (totals.get(key) ?? 0) + magnitude(tx, rates));
  }
  return [...totals.entries()]
    .map(([key, amount]) => ({ key, amount }))
    .sort((left, right) => right.amount - left.amount);
}

function typeLabel(
  typeField: "income_type" | "expense_type",
  value: string,
  t: ReturnType<typeof useTranslations<"finance">>,
): string {
  if (value === "") {
    return t("unspecified");
  }
  if (typeField === "income_type" && isIncomeType(value)) {
    return t(`incomeTypes.${value}`);
  }
  if (typeField === "expense_type" && isExpenseType(value)) {
    return t(`expenseTypes.${value}`);
  }
  return value;
}
