export function formatAed(amount: string | number): string {
  const value = typeof amount === "string" ? Number.parseFloat(amount) : amount;
  if (Number.isNaN(value)) return "GEL 0.00";
  return `GEL ${value.toFixed(2)}`;
}

export function formatPriceDelta(delta: string | number): string {
  const value = typeof delta === "string" ? Number.parseFloat(delta) : delta;
  if (Number.isNaN(value) || value === 0) return "";
  const sign = value > 0 ? "+" : "−";
  return `${sign}GEL ${Math.abs(value).toFixed(2)}`;
}

export function formatTimeslot(start: string, end: string): string {
  const [sh, sm] = start.split(":");
  const [eh, em] = end.split(":");
  return `${sh}:${sm} – ${eh}:${em}`;
}

export function formatTimeslotDateLabel(date: string): string {
  const d = new Date(`${date}T00:00:00`);
  return d.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function formatOrderTimeslot(startIso: string | null, endIso: string | null): string {
  if (!startIso || !endIso) return "";
  const start = new Date(startIso);
  const end = new Date(endIso);
  const datePart = start.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const timeOpts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  };
  const startTime = start.toLocaleTimeString("en-US", timeOpts);
  const endTime = end.toLocaleTimeString("en-US", timeOpts);
  return `${datePart} ${startTime} – ${endTime}`;
}

export function todayIsoDate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
