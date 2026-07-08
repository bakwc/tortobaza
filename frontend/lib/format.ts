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
