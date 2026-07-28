// The lawn is in Topeka, KS. These pages are server-rendered, and the web
// container runs in UTC, so date formatting must name the zone explicitly or a
// 7:32 PM Central timestamp renders as the next day's 12:32 AM. Single-location
// app: the backend already hardcodes this same zone.
export const LAWN_TIME_ZONE = "America/Chicago";

function pad(value: number) {
  return String(value).padStart(2, "0");
}

export function toLocalDatetimeInputValue(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}