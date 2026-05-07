import type { Metadata } from "next";
import Link from "next/link";
import { Plus, Droplets } from "lucide-react";

import { listIrrigationZones } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Irrigation Zones" };

export default async function ZonesPage() {
  let zones = await listIrrigationZones().catch(() => []);
  zones = zones.sort((a, b) => a.zone_number - b.zone_number);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Irrigation Zones</h1>
          <p className="text-sm text-muted-foreground">{zones.length} zone{zones.length !== 1 ? "s" : ""}</p>
        </div>
        <Button asChild size="sm">
          <Link href="/zones/new"><Plus className="mr-1 h-4 w-4" />New zone</Link>
        </Button>
      </div>

      {/* Desktop table */}
      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Head type</TableHead>
              <TableHead>Sun</TableHead>
              <TableHead>Slope</TableHead>
              <TableHead className="text-right">Sq ft</TableHead>
              <TableHead className="text-right">Precip (in/hr)</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {zones.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  No zones yet. Add one or run Rachio Connect from the API.
                </TableCell>
              </TableRow>
            )}
            {zones.map((z) => (
              <TableRow key={z.id}>
                <TableCell className="font-mono">{z.zone_number}</TableCell>
                <TableCell className="font-medium">{z.name}</TableCell>
                <TableCell>{z.head_type.replace(/_/g, " ")}</TableCell>
                <TableCell>{z.sun_exposure.replace(/_/g, " ")}</TableCell>
                <TableCell>{z.slope}</TableCell>
                <TableCell className="text-right">{z.sqft ?? "–"}</TableCell>
                <TableCell className="text-right">{z.precipitation_rate_in_per_hr ?? "–"}</TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/zones/${z.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <div className="space-y-3 md:hidden">
        {zones.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No zones yet.</p>
        )}
        {zones.map((z) => (
          <Link key={z.id} href={`/zones/${z.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <Droplets className="h-5 w-5 shrink-0 text-blue-500" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{z.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Zone {z.zone_number} · {z.head_type.replace(/_/g, " ")} · {z.sun_exposure.replace(/_/g, " ")}
                  </p>
                </div>
                {z.rachio_zone_id && (
                  <Badge variant="secondary" className="shrink-0 text-xs">Rachio</Badge>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
