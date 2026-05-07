import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getCulturalPractice, listEquipment } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CulturalDetailClient } from "../_components/cultural-detail-client";

export const metadata: Metadata = { title: "Practice Detail" };

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export default async function CulturalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let practice;
  try {
    practice = await getCulturalPractice(id);
  } catch {
    notFound();
  }
  const equipment = await listEquipment().catch(() => []);
  const usedEquipment = equipment.find((e) => e.id === practice.equipment_id);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/cultural"><ArrowLeft className="mr-1 h-4 w-4" />Cultural</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold capitalize">{practice.practice_type}</h1>
          <p className="text-sm text-muted-foreground">{formatDate(practice.performed_at)}</p>
        </div>
        <CulturalDetailClient practice={practice} equipment={equipment} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Details</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-xs text-muted-foreground">Practice</p>
              <Badge variant="secondary" className="mt-1">{practice.practice_type}</Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Equipment</p>
              <p className="text-sm font-medium">
                {usedEquipment ? `${usedEquipment.make} ${usedEquipment.model}` : "–"}
              </p>
            </div>
          </CardContent>
        </Card>
        {practice.notes && (
          <Card>
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{practice.notes}</p></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
