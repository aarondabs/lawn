// The lawn is in Topeka, KS. These pages are server-rendered, and the web
// container runs in UTC, so date handling must name the zone explicitly or a
// 7:32 PM Central timestamp renders as the next day's 12:32 AM. Single-location
// app: the backend already hardcodes this same zone.
export const LAWN_TIME_ZONE = "America/Chicago";

// h23 avoids "24:00" at midnight; en-CA keeps parts numeric.
const inputFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: LAWN_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

// Lawn-local wall clock of an instant, as a datetime-local input value
// ("YYYY-MM-DDTHH:mm"). Pinned to LAWN_TIME_ZONE, not the runtime's zone, so
// it is correct wherever it runs.
export function toLocalDatetimeInputValue(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const parts: Partial<Record<Intl.DateTimeFormatPartTypes, string>> = {};
  for (const part of inputFormatter.formatToParts(date)) {
    parts[part.type] = part.value;
  }
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

// Inverse of the above: a datetime-local value, read as lawn-local wall clock,
// to a UTC ISO instant for the API. Starts from the UTC reading of the string
// and corrects by the rendered difference — one pass lands it; the second
// covers a DST edge.
export function lawnLocalInputToISOString(value: string) {
  let ts = Date.parse(`${value}:00Z`);
  for (let i = 0; i < 2; i += 1) {
    const rendered = toLocalDatetimeInputValue(new Date(ts));
    if (rendered === value) break;
    ts += Date.parse(`${value}:00Z`) - Date.parse(`${rendered}:00Z`);
  }
  return new Date(ts).toISOString();
}
