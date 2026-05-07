import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getEquipment } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EquipmentDetailClient } from "../_components/equipment-detail-client";

export const metadata: Metadata = { title: "Equipment Detail" };

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? "–"}</p>
    </div>
  );
}

export default async function EquipmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let equipment;
  try {
    equipment = await getEquipment(id);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/equipment"><ArrowLeft className="mr-1 h-4 w-4" />Equipment</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{equipment.make} {equipment.model}</h1>
          <Badge variant="outline" className="mt-1">{equipment.type}</Badge>
        </div>
        <EquipmentDetailClient equipment={equipment} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Details</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Type" value={equipment.type} />
            <DetailRow label="Make" value={equipment.make} />
            <DetailRow label="Model" value={equipment.model} />
            <DetailRow label="Last calibration" value={equipment.last_calibration_date} />
          </CardContent>
        </Card>
        {equipment.notes && (
          <Card>
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{equipment.notes}</p></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
