import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getTreatment, listProducts, listEquipment } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TreatmentDetailClient } from "../_components/treatment-detail-client";
import {
  APPLICATION_METHOD_LABELS,
  amountUnitLabel,
  granularAmountUsed,
  rateUnitLabel,
} from "@/lib/enums";

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
  const productMap = Object.fromEntries(products.map((p) => [p.id, p]));
  const treatmentProducts = [...treatment.products].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  const title = treatmentProducts.length
    ? `${productMap[treatmentProducts[0].product_id]?.name ?? "Treatment"}${treatmentProducts.length > 1 ? ` +${treatmentProducts.length - 1}` : ""}`
    : "Treatment";
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
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">{formatDate(treatment.applied_at)}</p>
        </div>
        <TreatmentDetailClient treatment={treatment} products={products} equipment={equipment} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Application</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Area treated" value={`${treatment.area_treated_sqft.toLocaleString()} sq ft`} />
            <DetailRow label="Equipment" value={equip ? `${equip.make} ${equip.model}` : null} />
            <DetailRow label="Applicator" value={treatment.applicator} />
            <DetailRow
              label="Method"
              value={
                APPLICATION_METHOD_LABELS[
                  treatment.application_method as keyof typeof APPLICATION_METHOD_LABELS
                ] ?? treatment.application_method
              }
            />
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

        {treatment.fills.length > 0 && (
          <Card className="sm:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">
                Tank Fills ({treatment.fills.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {treatment.fills.map((fill) => (
                <div key={fill.id} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="font-medium">Fill {fill.fill_number}</p>
                    <p className="text-sm text-muted-foreground">
                      {fill.total_mix_volume} {fill.total_mix_volume_unit} @ {fill.calibrated_rate_snapshot}{" "}
                      {rateUnitLabel(fill.calibrated_rate_unit_snapshot)} ·{" "}
                      <span className="font-medium text-foreground">
                        {Math.round(fill.area_covered_sqft).toLocaleString()} sq ft
                      </span>
                    </p>
                  </div>
                  <div className="mt-2 space-y-1">
                    {fill.products.map((fp) => (
                      <div
                        key={fp.product_id}
                        className="flex flex-wrap justify-between gap-2 text-sm"
                      >
                        <span>{productMap[fp.product_id]?.name ?? "Unknown product"}</span>
                        <span className="text-muted-foreground">
                          {fp.amount_used} {amountUnitLabel(fp.amount_used_unit)}
                          {fp.effective_rate_per_1000 != null && (
                            <>
                              {" · "}
                              {fp.effective_rate_per_1000.toFixed(2)}{" "}
                              {amountUnitLabel(fp.amount_used_unit)} / 1,000 sq ft
                            </>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                  {fill.notes ? (
                    <p className="mt-2 text-sm text-muted-foreground">Notes: {fill.notes}</p>
                  ) : null}
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {treatmentProducts.length > 0 && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Products</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {treatmentProducts.map((tp) => {
                const product = productMap[tp.product_id];
                return (
                  <div key={tp.product_id} className="rounded-md border p-3">
                    <p className="font-medium">{product?.name ?? "Unknown product"}</p>
                    <p className="text-sm text-muted-foreground">
                      Rate: {tp.rate_applied} {rateUnitLabel(tp.rate_unit)}
                      {(() => {
                        // Derived, never stored: rate x area. Depends on two
                        // mutable columns, so computing it here avoids drift.
                        const used = granularAmountUsed(
                          tp.rate_applied,
                          tp.rate_unit,
                          treatment.area_treated_sqft,
                        );
                        return used
                          ? ` · ${used.amount.toFixed(2)} ${amountUnitLabel(used.unit)} used`
                          : null;
                      })()}
                    </p>
                    {tp.notes ? <p className="text-sm text-muted-foreground">Notes: {tp.notes}</p> : null}
                    {product ? (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge variant="secondary">{product.product_type.replace(/_/g, " ")}</Badge>
                        <span className="text-sm text-muted-foreground">Label: {product.label_rate} {rateUnitLabel(product.label_rate_unit)}</span>
                        {product.reentry_interval_hours != null ? (
                          <span className="text-sm text-muted-foreground">REI: {product.reentry_interval_hours} hrs</span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
