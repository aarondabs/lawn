import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getSoilTest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SoilTestDetailClient } from "../_components/soil-test-detail-client";

export const metadata: Metadata = { title: "Soil Test Detail" };

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? "–"}</p>
    </div>
  );
}

export default async function SoilTestDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let soilTest;
  try {
    soilTest = await getSoilTest(id);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/soil-tests"><ArrowLeft className="mr-1 h-4 w-4" />Soil Tests</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{soilTest.lab_name}</h1>
          <p className="text-sm text-muted-foreground">{soilTest.sample_date}</p>
        </div>
        <SoilTestDetailClient soilTest={soilTest} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Key values</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="pH" value={soilTest.ph} />
            <DetailRow label="Organic matter (%)" value={soilTest.organic_matter_pct} />
            <DetailRow label="CEC" value={soilTest.cec} />
            <DetailRow label="Phosphorus (ppm)" value={soilTest.phosphorus_ppm} />
            <DetailRow label="Potassium (ppm)" value={soilTest.potassium_ppm} />
            <DetailRow label="Calcium (ppm)" value={soilTest.calcium_ppm} />
            <DetailRow label="Magnesium (ppm)" value={soilTest.magnesium_ppm} />
            <DetailRow label="Sulfur (ppm)" value={soilTest.sulfur_ppm} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Micronutrients</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Iron (ppm)" value={soilTest.iron_ppm} />
            <DetailRow label="Manganese (ppm)" value={soilTest.manganese_ppm} />
            <DetailRow label="Zinc (ppm)" value={soilTest.zinc_ppm} />
            <DetailRow label="Copper (ppm)" value={soilTest.copper_ppm} />
            <DetailRow label="Boron (ppm)" value={soilTest.boron_ppm} />
          </CardContent>
        </Card>
        {soilTest.lab_recommendations && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Lab recommendations</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{soilTest.lab_recommendations}</p></CardContent>
          </Card>
        )}
        {soilTest.notes && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{soilTest.notes}</p></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
