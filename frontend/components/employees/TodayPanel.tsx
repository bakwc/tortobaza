"use client";

import { useFormatter, useTranslations } from "next-intl";
import { QueryState } from "@/components/menu/ui";
import { useScheduleToday } from "@/hooks/useSchedule";
import type { ScheduleToday } from "@/lib/api/types";

function parseDay(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function initial(name: string): string {
  const trimmed = name.trim();
  return trimmed ? trimmed.charAt(0).toLocaleUpperCase() : "?";
}

export function TodayPanel() {
  const overview = useScheduleToday();
  return (
    <QueryState isLoading={overview.isLoading} isError={overview.isError}>
      {overview.data ? <TodayCards data={overview.data} /> : null}
    </QueryState>
  );
}

function TodayCards({ data }: { data: ScheduleToday }) {
  const t = useTranslations("employees");
  const format = useFormatter();
  const onSite = data.today_employees.filter((person) => person.on_site).length;
  const dateLabel = (value: string) =>
    format.dateTime(parseDay(value), { weekday: "short", day: "numeric", month: "short" });

  return (
    <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
      <section className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold text-[var(--ink)]">
            {t("todayTitle")}
            <span className="ml-2 text-sm font-normal text-[var(--muted-2)]">{dateLabel(data.today)}</span>
          </h2>
          {data.today_employees.length > 0 ? (
            <span className="text-sm text-[var(--muted-2)]">
              {t("onSiteCount", { on: onSite, total: data.today_employees.length })}
            </span>
          ) : null}
        </div>
        {data.today_employees.length === 0 ? (
          <p className="text-sm text-[var(--muted-2)]">{t("todayEmpty")}</p>
        ) : (
          <ul className="grid gap-2">
            {data.today_employees.map((person) => (
              <li key={person.id} className="flex items-center gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--brand)]/10 text-sm font-semibold text-[var(--ink)]">
                  {initial(person.name)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex min-w-0 flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-medium text-[var(--ink)]">{person.name}</span>
                    {person.scheduled ? null : (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
                        {t("offSchedule")}
                      </span>
                    )}
                  </span>
                  {person.position ? (
                    <span className="block truncate text-xs text-[var(--muted-2)]">{person.position}</span>
                  ) : null}
                </span>
                <Presence person={person} />
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-sm md:rounded-3xl">
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold text-[var(--ink)]">
            {t("tomorrowTitle")}
            <span className="ml-2 text-sm font-normal text-[var(--muted-2)]">{dateLabel(data.tomorrow)}</span>
          </h2>
          <span className="text-sm tabular-nums text-[var(--muted-2)]">{data.tomorrow_employees.length}</span>
        </div>
        {data.tomorrow_employees.length === 0 ? (
          <p className="text-sm text-[var(--muted-2)]">{t("tomorrowEmpty")}</p>
        ) : (
          <ul className="grid gap-2">
            {data.tomorrow_employees.map((person) => (
              <li key={person.id} className="min-w-0">
                <span className="block truncate text-sm font-medium text-[var(--ink)]">{person.name}</span>
                {person.position ? (
                  <span className="block truncate text-xs text-[var(--muted-2)]">{person.position}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Presence({ person }: { person: ScheduleToday["today_employees"][number] }) {
  const t = useTranslations("employees");
  if (person.on_site) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-950">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        {t("onSiteSince", { time: person.arrival ?? "" })}
      </span>
    );
  }
  if (person.departure) {
    return (
      <span className="shrink-0 rounded-full bg-neutral-200 px-2.5 py-1 text-xs font-medium tabular-nums text-neutral-800">
        {person.arrival}–{person.departure}
      </span>
    );
  }
  return (
    <span className="shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 text-xs text-neutral-500">
      {t("notArrived")}
    </span>
  );
}
