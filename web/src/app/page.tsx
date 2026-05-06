import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getHealth } from "@/lib/api";

export default async function Home() {
  let healthState = "unavailable";

  try {
    const health = await getHealth();
    healthState = `${health.status}${health.db ? ` (${health.db})` : ""}`;
  } catch {
    healthState = "offline";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Task 8 shell with navigation and API wiring.</p>
        </div>
        <Badge variant="secondary">API: {healthState}</Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Weather</CardDescription>
            <CardTitle className="text-sm">Current</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-6 w-24" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Irrigation</CardDescription>
            <CardTitle className="text-sm">7-day total</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-6 w-16" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Treatments</CardDescription>
            <CardTitle className="text-sm">Last application</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-6 w-28" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Reminders</CardDescription>
            <CardTitle className="text-sm">Upcoming</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-6 w-12" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
