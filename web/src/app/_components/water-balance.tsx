import { CloudRain, Droplets } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getWaterBalance, type WaterBalance } from "@/lib/api";

function inches(n: number) {
  return `${n.toFixed(2)}"`;
}

export async function WaterBalanceWidget() {
  let data: WaterBalance | null = null;
  try {
    data = await getWaterBalance();
  } catch {
    return null;
  }

  const windows = [
    { label: "7 days", w: data.windows["7"] },
    { label: "14 days", w: data.windows["14"] },
    { label: "30 days", w: data.windows["30"] },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <CloudRain className="h-4 w-4" />
          Water balance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          {windows.map(({ label, w }) => (
            <div key={label} className="rounded-md border p-3">
              <p className="text-xs font-medium text-muted-foreground">{label}</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">{inches(w.total_in)}</p>
              <p className="text-xs text-muted-foreground">
                {inches(w.rainfall_in)} rain + {inches(w.lawn_irrigation_in)} irrig.
              </p>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Lawn-wide, turf zones only. Rainfall from weather; irrigation averaged across turf zones.
        </p>
        {data.drip_7d.event_count > 0 && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Droplets className="h-3.5 w-3.5 shrink-0" />
            Drip zones ran {data.drip_7d.event_count}× in the last 7 days (excluded from the lawn total)
          </p>
        )}
      </CardContent>
    </Card>
  );
}
