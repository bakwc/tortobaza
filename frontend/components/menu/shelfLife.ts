const DAY_SECONDS = 86400;
const HOUR_SECONDS = 3600;

export function formatShelfLife(
  seconds: number,
  daysText: (count: number) => string,
  hoursText: (count: number) => string,
): string {
  const days = Math.floor(seconds / DAY_SECONDS);
  const hours = Math.floor((seconds % DAY_SECONDS) / HOUR_SECONDS);
  const parts: string[] = [];
  if (days > 0) parts.push(daysText(days));
  if (hours > 0) parts.push(hoursText(hours));
  return parts.join(" ");
}

export function shelfLifeDraft(seconds: number | null): { days: string; hours: string } {
  if (seconds === null) return { days: "", hours: "" };
  const days = Math.floor(seconds / DAY_SECONDS);
  const hours = Math.floor((seconds % DAY_SECONDS) / HOUR_SECONDS);
  return {
    days: days === 0 ? "" : String(days),
    hours: hours === 0 ? "" : String(hours),
  };
}

export function shelfLifeSeconds(days: string, hours: string): number | null {
  if (days.trim() === "" && hours.trim() === "") return null;
  const dayCount = days.trim() === "" ? 0 : Number(days);
  const hourCount = hours.trim() === "" ? 0 : Number(hours);
  return dayCount * DAY_SECONDS + hourCount * HOUR_SECONDS;
}
