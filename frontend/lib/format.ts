const BUSINESS_TIMEZONE = "Asia/Tbilisi";

function intlLocaleTag(locale: string): string {
  if (locale === "ka") return "ka-GE";
  if (locale === "ru") return "ru-RU";
  return "en-GB";
}

export function formatAed(amount: string | number): string {
  const value = typeof amount === "string" ? Number.parseFloat(amount) : amount;
  if (Number.isNaN(value)) return "0.00 ₾";
  return `${value.toFixed(2)} ₾`;
}

export function formatPriceDelta(delta: string | number): string {
  const value = typeof delta === "string" ? Number.parseFloat(delta) : delta;
  if (Number.isNaN(value) || value === 0) return "";
  const sign = value > 0 ? "+" : "−";
  return `${sign}${Math.abs(value).toFixed(2)} ₾`;
}

export function formatTimeslot(start: string, end: string): string {
  const [sh, sm] = start.split(":");
  const [eh, em] = end.split(":");
  return `${sh}:${sm} – ${eh}:${em}`;
}

export function formatTimeslotDateLabel(date: string, locale: string): string {
  const d = new Date(`${date}T00:00:00`);
  return d.toLocaleDateString(intlLocaleTag(locale), {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function formatOrderTimeslot(
  startIso: string | null,
  endIso: string | null,
  locale: string,
): string {
  if (!startIso || !endIso) return "";
  const start = new Date(startIso);
  const end = new Date(endIso);
  const tag = intlLocaleTag(locale);
  const datePart = start.toLocaleDateString(tag, {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: BUSINESS_TIMEZONE,
  });
  const timeOpts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    hour12: locale === "en",
    timeZone: BUSINESS_TIMEZONE,
  };
  const startTime = start.toLocaleTimeString(tag, timeOpts);
  const endTime = end.toLocaleTimeString(tag, timeOpts);
  return `${datePart} ${startTime} – ${endTime}`;
}

export function todayIsoDate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function formatAttendanceDate(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

export function formatAttendanceTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: BUSINESS_TIMEZONE,
  });
}

export function getTbilisiTodayIsoDate(): string {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: BUSINESS_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(new Date());
}

export function formatCrmDate(dateStr: string, locale: string): string {
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toLocaleDateString(intlLocaleTag(locale), {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function mondayFirstWeekdayLabels(locale: string): string[] {
  const tag = intlLocaleTag(locale);
  const monday = new Date(Date.UTC(2021, 5, 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setUTCDate(monday.getUTCDate() + i);
    return d.toLocaleDateString(tag, { weekday: "short", timeZone: "UTC" });
  });
}

export function formatCrmMonthYear(year: number, month: number, locale: string): string {
  const d = new Date(Date.UTC(year, month - 1, 1));
  return d.toLocaleDateString(intlLocaleTag(locale), {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function parseIsoDateParts(iso: string): { year: number; month: number; day: number } {
  const [yearStr, monthStr, dayStr] = iso.split("-");
  return { year: Number(yearStr), month: Number(monthStr), day: Number(dayStr) };
}

export function toIsoDate(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function daysInUtcMonth(year: number, month: number): number {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

export function mondayFirstOffset(year: number, month: number): number {
  const dow = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  return (dow + 6) % 7;
}
