import type { Metadata } from "next";
import Link from "next/link";
import { Plus, Wrench } from "lucide-react";

import { listEquipment } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Equipment" };

export default async function EquipmentPage() {
  const equipment = await listEquipment().catch(() => []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Equipment</h1>
          <p className="text-sm text-muted-foreground">{equipment.length} item{equipment.length !== 1 ? "s" : ""}</p>
        </div>
        <Button asChild size="sm">
          <Link href="/equipment/new"><Plus className="mr-1 h-4 w-4" />Add</Link>
        </Button>
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Make / Model</TableHead>
              <TableHead>Last calibration</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {equipment.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">No equipment yet.</TableCell>
              </TableRow>
            )}
            {equipment.map((e) => (
              <TableRow key={e.id}>
                <TableCell><Badge variant="outline">{e.type}</Badge></TableCell>
                <TableCell className="font-medium">{e.make} {e.model}</TableCell>
                <TableCell>{e.last_calibration_date ?? "–"}</TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/equipment/${e.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {equipment.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No equipment yet.</p>
        )}
        {equipment.map((e) => (
          <Link key={e.id} href={`/equipment/${e.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <Wrench className="h-5 w-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{e.make} {e.model}</p>
                  <p className="text-xs text-muted-foreground">{e.type}</p>
                </div>
                {e.last_calibration_date && (
                  <span className="shrink-0 text-xs text-muted-foreground">Cal: {e.last_calibration_date}</span>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
