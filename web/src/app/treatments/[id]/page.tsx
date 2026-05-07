import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getTreatment, listProducts, listEquipment } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TreatmentDetailClient } from "../_components/treatment-detail-client";

export const metadata: Metadata = { title: "Treatment Detail" };

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? "–"}</p>
    </div>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export default async function TreatmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let treatment;
  try {
    treatment = await getTreatment(id);
  } catch {
    notFound();
  }
  const [products, equipment] = await Promise.all([
    listProducts().catch(() => []),
    listEquipment().catch(() => []),
  ]);
  const product = products.find((p) => p.id === treatment.product_id);
  const equip = equipment.find((e) => e.id === treatment.equipment_id);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/treatments"><ArrowLeft className="mr-1 h-4 w-4" />Treatments</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{product?.name ?? "Treatment"}</h1>
          <p className="text-sm text-muted-foreground">{formatDate(treatment.applied_at)}</p>
        </div>
        <TreatmentDetailClient treatment={treatment} products={products} equipment={equipment} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Application</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Product" value={product?.name} />
            <DetailRow label="Rate applied" value={`${treatment.rate_applied} ${treatment.rate_unit} / 1000 sq ft`} />
            <DetailRow label="Area treated" value={`${treatment.area_treated_sqft.toLocaleString()} sq ft`} />
            <DetailRow label="Equipment" value={equip ? `${equip.make} ${equip.model}` : null} />
            <DetailRow label="Applicator" value={treatment.applicator} />
            <DetailRow label="Target" value={treatment.target} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Conditions</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Temp (°F)" value={treatment.weather_temp_f} />
            <DetailRow label="Wind (mph)" value={treatment.weather_wind_mph} />
            <DetailRow label="Conditions" value={treatment.weather_conditions} />
          </CardContent>
        </Card>
        {treatment.notes && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{treatment.notes}</p></CardContent>
          </Card>
        )}
        {product && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Product info</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Badge variant="secondary">{product.product_type.replace(/_/g, " ")}</Badge>
              <span className="text-sm text-muted-foreground">Label rate: {product.label_rate} {product.label_rate_unit}</span>
              {product.reentry_interval_hours != null && (
                <span className="text-sm text-muted-foreground">REI: {product.reentry_interval_hours} hrs</span>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
