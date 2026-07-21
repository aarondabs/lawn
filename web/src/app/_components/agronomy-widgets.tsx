import { AlertTriangle, Droplets, Gauge, Scissors, Sprout, Thermometer } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardWidgets, type DashboardWidgets } from "@/lib/api";

function prettyDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "3 days ago" / "today" / "--" when unknown. */
function daysAgoLabel(days: number | null): string {
  if (days == null) return "--";
  if (days === 0) return "today";
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

const TREND_LABEL: Record<string, string> = { rising: "↑ rising", falling: "↓ falling", steady: "→ steady" };

function StatCard({
  icon,
  title,
  value,
  sub,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export async function AgronomyWidgets() {
  let data: DashboardWidgets | null = null;
  try {
    data = await getDashboardWidgets();
  } catch {
    return null;
  }

  const { gdd, days_since, soil_temp, outstanding_cautions, irrigation_skips_7d } = data;

  return (
    <div className="space-y-4">
      {outstanding_cautions.length > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-500">
              <AlertTriangle className="h-4 w-4" />
              Outstanding cautions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {outstanding_cautions.map((c) => (
              <div key={c.code} className="text-sm">
                <span className="font-medium">{c.title}.</span>{" "}
                <span className="text-muted-foreground">{c.message}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Gauge className="h-4 w-4" />}
          title="Growing degree days"
          value={gdd.days_counted > 0 ? Math.round(gdd.since_green_up).toLocaleString() : "--"}
          sub={
            gdd.days_counted > 0
              ? `base 50°F, since ${prettyDate(gdd.green_up_date)}${
                  gdd.latest_day != null ? ` · +${Math.round(gdd.latest_day)} latest day` : ""
                }`
              : "no data since green-up yet"
          }
        />
        <StatCard
          icon={<Scissors className="h-4 w-4" />}
          title="Last mow"
          value={daysAgoLabel(days_since.mow)}
          sub={days_since.last_mow_at ? prettyDate(days_since.last_mow_at) : "nothing logged"}
        />
        <StatCard
          icon={<Sprout className="h-4 w-4" />}
          title="Last treatment"
          value={daysAgoLabel(days_since.treatment)}
          sub={[
            days_since.fertilizer != null ? `fert ${daysAgoLabel(days_since.fertilizer)}` : null,
            days_since.herbicide != null ? `herb ${daysAgoLabel(days_since.herbicide)}` : null,
          ]
            .filter(Boolean)
            .join(" · ") || undefined}
        />
        <StatCard
          icon={<Thermometer className="h-4 w-4" />}
          title="Soil temp"
          value={soil_temp.latest_f != null ? `${Math.round(soil_temp.latest_f)}°F` : "--"}
          sub={
            soil_temp.avg_7d_f != null
              ? `7-day avg ${soil_temp.avg_7d_f}°F${soil_temp.trend ? ` · ${TREND_LABEL[soil_temp.trend]}` : ""}`
              : "no readings"
          }
        />
      </div>

      {irrigation_skips_7d.count > 0 && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Droplets className="h-4 w-4 shrink-0" />
          Rachio skipped watering {irrigation_skips_7d.count}× in the last 7 days
          {irrigation_skips_7d.recent[0]?.summary ? ` — ${irrigation_skips_7d.recent[0].summary}` : ""}
        </p>
      )}
    </div>
  );
}

export function AgronomyWidgetsSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="py-6">
            <div className="h-4 w-24 animate-pulse rounded bg-muted" />
            <div className="mt-3 h-7 w-16 animate-pulse rounded bg-muted" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
