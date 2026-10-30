"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const DONUT_SIZE = 260;
const DONUT_CENTER = 130;
const DONUT_OUTER = 118;
const DONUT_INNER = 70;
const DONUT_TOP = 7;
const REST_KEY = "__rest__";
export const REST_COLOR = "#b5b5b5";
export const PIE_COLORS = [
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

export type SharePieRow = {
  key: string;
  label: string;
  value: number;
};

type ColoredRow = SharePieRow & {
  color: string;
};

type DrawnSlice = ColoredRow & {
  percent: number;
  path: string;
  labelX: number;
  labelY: number;
};

export function SharePie({
  rows,
  collapse,
  restLabel,
}: {
  rows: SharePieRow[];
  collapse: boolean;
  restLabel: string;
}) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const percents = total === 0 ? rows.map(() => 0) : percentShares(rows.map((row) => row.value), total);
  const max = rows.reduce((peak, row) => (row.value > peak ? row.value : peak), 0);
  const collapseTail = collapse && rows.length > DONUT_TOP;
  const slices = drawSlices(donutRows(rows, collapseTail, restLabel));
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
            const hovered = sliceIsHovered(slice.key, hoveredKey, rows, collapseTail);
            const dimmed = hoveredKey !== null && !hovered;
            return (
              <g key={slice.key} onMouseEnter={() => setHoveredKey(slice.key)}>
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
                  fontSize={centerValueSize(focus.value)}
                  fontWeight={600}
                >
                  {focus.value}
                </text>
              </>
            ) : (
              <text
                x={DONUT_CENTER}
                y={DONUT_CENTER}
                textAnchor="middle"
                dominantBaseline="central"
                className="fill-[var(--ink)]"
                fontSize={centerValueSize(total)}
                fontWeight={600}
              >
                {total}
              </text>
            )}
          </g>
        </svg>
      ) : null}
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        {rows.map((row, index) => {
          const highlighted = rowHighlighted(row.key, index, hoveredKey, collapseTail);
          const color = rowColor(index, collapseTail);
          return (
            <div
              key={row.key}
              onMouseEnter={() => setHoveredKey(row.key)}
              className={cn("min-w-0 rounded-lg px-1.5 py-1", highlighted && "bg-[var(--cream-soft)]")}
            >
              <div className="flex min-w-0 items-baseline justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                  <span className="min-w-0 truncate text-[var(--ink)]">{row.label}</span>
                </span>
                <span className="flex shrink-0 items-baseline gap-2 tabular-nums">
                  <span className="font-medium text-[var(--ink)]">{row.value}</span>
                  <span className="w-11 text-right text-[var(--muted-2)]">{percents[index]}%</span>
                </span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-[var(--line)]">
                <div
                  className="h-1.5 rounded-full transition-[width]"
                  style={{
                    width: max === 0 ? "0%" : `${(row.value / max) * 100}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function donutRows(rows: SharePieRow[], collapseTail: boolean, restLabel: string): ColoredRow[] {
  const colored = rows.map((row, index) => ({ ...row, color: rowColor(index, false) }));
  if (!collapseTail) return colored;
  const head = colored.slice(0, DONUT_TOP);
  const value = rows.slice(DONUT_TOP).reduce((sum, row) => sum + row.value, 0);
  return [...head, { key: REST_KEY, label: restLabel, value, color: REST_COLOR }];
}

function rowColor(index: number, collapseTail: boolean): string {
  if (collapseTail && index >= DONUT_TOP) return REST_COLOR;
  return PIE_COLORS[index % PIE_COLORS.length];
}

function drawSlices(slices: ColoredRow[]): DrawnSlice[] {
  const positive = slices.filter((slice) => slice.value > 0);
  const total = positive.reduce((sum, slice) => sum + slice.value, 0);
  if (total === 0) return [];
  const percents = percentShares(
    positive.map((slice) => slice.value),
    total,
  );
  let angle = -Math.PI / 2;
  return positive.map((slice, index) => {
    const sweep = (slice.value / total) * Math.PI * 2;
    const start = angle;
    const end = angle + sweep;
    angle = end;
    const mid = start + sweep / 2;
    const labelAt = polar(DONUT_CENTER, DONUT_CENTER, (DONUT_OUTER + DONUT_INNER) / 2, mid);
    return {
      key: slice.key,
      label: slice.label,
      value: slice.value,
      color: slice.color,
      percent: percents[index],
      path: pieSlice(DONUT_CENTER, DONUT_CENTER, DONUT_OUTER, DONUT_INNER, start, end),
      labelX: labelAt.x,
      labelY: labelAt.y,
    };
  });
}

function centerFocus(hoveredKey: string | null, rows: SharePieRow[], slices: DrawnSlice[]): SharePieRow | null {
  if (hoveredKey === null) return null;
  return rows.find((row) => row.key === hoveredKey) ?? slices.find((slice) => slice.key === hoveredKey) ?? null;
}

function sliceIsHovered(sliceKey: string, hoveredKey: string | null, rows: SharePieRow[], collapseTail: boolean): boolean {
  if (hoveredKey === null) return false;
  if (sliceKey === hoveredKey) return true;
  if (!collapseTail || sliceKey !== REST_KEY) return false;
  const index = rows.findIndex((row) => row.key === hoveredKey);
  return index >= DONUT_TOP;
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

function centerValueSize(value: number): number {
  const length = String(value).length;
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
