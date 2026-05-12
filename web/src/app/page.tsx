import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardSummary, getHealth } from "@/lib/api";

function prettyDate(dateText: string) {
  return new Date(dateText).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function shortWeekday(dateText: string) {
  return new Date(dateText).toLocaleDateString("en-US", {
    weekday: "short",
  });
}

function prettyDateTime(dateText: string | null) {
  if (!dateText) {
    return "No data";
  }
  return new Date(dateText).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function fmtNumber(value: number | null | undefined, digits = 1) {
  if (value == null) {
    return "-";
  }
  return value.toFixed(digits);
}

export default async function Home() {
  let healthState = "unavailable";
  let dashboard = null;

  try {
    const health = await getHealth();
    healthState = `${health.status}${health.db ? ` (${health.db})` : ""}`;
  } catch {
    healthState = "offline";
  }

  try {
    dashboard = await getDashboardSummary();
  } catch {
    dashboard = null;
  }

  const weatherCurrent = dashboard?.weather.current;
  const todayForecast = dashboard?.weather.today_forecast;
  const next7DayForecast = dashboard?.weather.next_7_days ?? [];
  const forecastRainfall7d = dashboard?.weather.forecast_rainfall_7d_in ?? 0;
  const rainfall7d = dashboard?.weather.rainfall_7d_in ?? 0;
  const totalWater7d = dashboard?.irrigation.total_water_7d_in ?? 0;
  const turfIrrigation7d = dashboard?.irrigation.turf_avg_7d_in ?? 0;
  const zoneEvents7d = dashboard?.irrigation.zones_with_events_7d ?? 0;
  const excludedZones = dashboard?.irrigation.excluded_zone_numbers ?? [];
  const calibrationNote = dashboard?.irrigation.calibration_note ?? null;
  const zoneIrrigation = dashboard?.irrigation.zones ?? [];
  const lastTreatment = dashboard?.last_treatment;
  const lastCultural = dashboard?.last_cultural_by_type ?? [];
  const lastSoil = dashboard?.last_soil_test;
  const reminders = dashboard?.active_reminders ?? [];
  const quickActions = dashboard?.quick_actions ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Current conditions, recent activity, and quick actions.</p>
        </div>
        <Badge variant="secondary">API: {healthState}</Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Weather</CardDescription>
            <CardTitle className="text-sm">Current</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="text-2xl font-semibold">{fmtNumber(weatherCurrent?.temp_f)} F</p>
            <p className="text-muted-foreground">Humidity {fmtNumber(weatherCurrent?.humidity_pct, 0)}%</p>
            <p className="text-muted-foreground">Wind {fmtNumber(weatherCurrent?.wind_mph)} mph</p>
            <p className="text-muted-foreground">Observed {prettyDateTime(weatherCurrent?.observed_at ?? null)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Irrigation</CardDescription>
            <CardTitle className="text-sm">Total water depth (7d)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="text-2xl font-semibold">{fmtNumber(totalWater7d, 2)} in</p>
            <p className="text-muted-foreground">Rainfall {fmtNumber(rainfall7d, 2)} in</p>
            <p className="text-muted-foreground">Turf irrigation avg {fmtNumber(turfIrrigation7d, 2)} in</p>
            <p className="text-muted-foreground">Zones with water events: {zoneEvents7d}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Treatments</CardDescription>
            <CardTitle className="text-sm">Last application</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {lastTreatment ? (
              <>
                <p className="font-medium">{lastTreatment.product_name}</p>
                <p className="text-muted-foreground">{prettyDate(lastTreatment.applied_at)}</p>
                <p className="text-muted-foreground">{lastTreatment.days_ago} day(s) ago</p>
              </>
            ) : (
              <p className="text-muted-foreground">No treatments logged yet.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardDescription>Reminders</CardDescription>
                <CardTitle className="text-sm">Upcoming</CardTitle>
              </div>
              <Button asChild variant="ghost" size="sm" className="text-xs">
                <Link href="/reminders">View all</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p className="text-2xl font-semibold">{reminders.length}</p>
            <p className="text-muted-foreground">Active reminders</p>
            {reminders[0] && (
              <p className="truncate text-muted-foreground">
                Next: {prettyDate(reminders[0].due_date)} · {reminders[0].description}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Today&apos;s Forecast</CardTitle>
            <CardDescription>Current day details plus 7-day outlook for planning and recommendations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="space-y-1">
              <p>Conditions: {todayForecast?.conditions ?? "No data"}</p>
              <p>High: {fmtNumber(todayForecast?.temp_high_f)} F</p>
              <p>Low: {fmtNumber(todayForecast?.temp_low_f)} F</p>
              <p>Precip chance: {fmtNumber(todayForecast?.precip_probability_pct, 0)}%</p>
              <p>Precip amount: {fmtNumber(todayForecast?.precip_amount_in, 2)} in</p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-medium">Next 7 Days</p>
                <p className="text-xs text-muted-foreground">Projected rain: {fmtNumber(forecastRainfall7d, 2)} in</p>
              </div>
              <div className="space-y-1">
                {next7DayForecast.map((day) => (
                  <div key={day.date} className="grid grid-cols-[3.5rem_1fr_auto] items-center gap-2 rounded-md border px-2 py-1">
                    <span className="font-medium">{shortWeekday(day.date)}</span>
                    <span className="truncate text-muted-foreground">{day.conditions ?? "No data"}</span>
                    <span className="text-right">
                      {fmtNumber(day.precip_probability_pct, 0)}% / {fmtNumber(day.precip_amount_in, 2)} in
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Irrigation by Zone (7d)</CardTitle>
            <CardDescription>
              Applied depth from recorded irrigation events. Turf-depth metric excludes zones {excludedZones.join(", ")}.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {zoneIrrigation.length === 0 && (
              <p className="text-muted-foreground">No irrigation events logged in the last 7 days.</p>
            )}
            {zoneIrrigation.map((zone) => (
              <div key={zone.zone_id} className="flex items-center justify-between">
                <span className="truncate pr-2">
                  {zone.zone_name}
                  {!zone.included_in_turf_budget ? " (excluded)" : ""}
                </span>
                <span className="font-medium">{fmtNumber(zone.inches, 2)} in</span>
              </div>
            ))}
            {calibrationNote && <p className="pt-2 text-xs text-muted-foreground">{calibrationNote}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Latest Cultural Practices</CardTitle>
            <CardDescription>Most recent entry by practice type</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {lastCultural.length === 0 && (
              <p className="text-muted-foreground">No cultural practices logged yet.</p>
            )}
            {lastCultural.map((item) => (
              <div key={item.id} className="flex items-center justify-between">
                <span className="capitalize">{item.practice_type.replace(/_/g, " ")}</span>
                <span className="text-muted-foreground">{item.days_ago} day(s) ago</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Latest Soil Test</CardTitle>
            <CardDescription>Recent key nutrient snapshot</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {lastSoil ? (
              <>
                <p>Sampled: {prettyDate(lastSoil.sample_date)}</p>
                <p>pH: {fmtNumber(lastSoil.ph, 1)}</p>
                <p>Organic matter: {fmtNumber(lastSoil.organic_matter_pct, 1)}%</p>
                <p>P: {fmtNumber(lastSoil.phosphorus_ppm, 1)} ppm</p>
                <p>K: {fmtNumber(lastSoil.potassium_ppm, 1)} ppm</p>
              </>
            ) : (
              <p className="text-muted-foreground">No soil tests logged yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Actions</CardTitle>
          <CardDescription>Most common logging tasks</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {quickActions.map((action) => (
            <Button asChild key={action.href} variant="secondary" size="sm">
              <Link href={action.href}>{action.label}</Link>
            </Button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
