import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getIrrigationZone } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ZoneDetailClient } from "../_components/zone-detail-client";

export const metadata: Metadata = { title: "Zone Detail" };

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? "–"}</p>
    </div>
  );
}

export default async function ZoneDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let zone;
  try {
    zone = await getIrrigationZone(id);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/zones"><ArrowLeft className="mr-1 h-4 w-4" />Zones</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{zone.name}</h1>
          <p className="text-sm text-muted-foreground">Zone {zone.zone_number}</p>
        </div>
        <ZoneDetailClient zone={zone} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Zone info</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Head type" value={zone.head_type.replace(/_/g, " ")} />
            <DetailRow label="Sun exposure" value={zone.sun_exposure.replace(/_/g, " ")} />
            <DetailRow label="Slope" value={zone.slope} />
            <DetailRow label="Area (sq ft)" value={zone.sqft} />
            <DetailRow label="Nozzle GPM" value={zone.nozzle_gpm} />
            <DetailRow label="Precip rate (in/hr)" value={zone.precipitation_rate_in_per_hr} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Integration</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <DetailRow label="Rachio zone ID" value={zone.rachio_zone_id} />
            <DetailRow label="Zone category" value={zone.zone_category.replace(/_/g, " ")} />
            <DetailRow label="Soil type override" value={zone.soil_type_override?.replace(/_/g, " ")} />
            {zone.rachio_zone_id && <Badge variant="secondary">Rachio connected</Badge>}
          </CardContent>
        </Card>
        {zone.notes && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{zone.notes}</p></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
