import type { Metadata } from "next";
import Link from "next/link";
import { FlaskConical } from "lucide-react";

import { getLawnProfile, listTreatments, listProducts, listEquipment, type Treatment } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { NewTreatmentDialog } from "./_components/new-treatment-dialog";
import { amountUnitLabel, rateUnitLabel } from "@/lib/enums";

export const metadata: Metadata = { title: "Treatments" };

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function productSummary(
  treatment: Treatment,
  productMap: Record<string, { name: string }>,
) {
  // Liquid treatments carry their products on the fills, not the treatment.
  if (treatment.fills.length > 0) {
    const names = [
      ...new Set(
        treatment.fills.flatMap((f) =>
          f.products.map((fp) => productMap[fp.product_id]?.name ?? "Unknown product"),
        ),
      ),
    ];
    if (names.length === 0) return "No products";
    return names.length === 1 ? names[0] : `${names[0]} +${names.length - 1} more`;
  }
  if (treatment.products.length === 0) return "No products";
  const sorted = [...treatment.products].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  const names = sorted
    .map((p) => productMap[p.product_id]?.name ?? "Unknown product")
    .filter((n, idx, arr) => arr.indexOf(n) === idx);
  if (names.length <= 1) return names[0] ?? "Unknown product";
  return `${names[0]} +${names.length - 1} more`;
}

function rateSummary(treatment: Treatment) {
  if (treatment.fills.length > 0) {
    const totalVolume = treatment.fills.reduce((sum, f) => sum + f.total_mix_volume, 0);
    const unit = treatment.fills[0]?.total_mix_volume_unit ?? "gal";
    const fills = treatment.fills.length;
    return `${totalVolume} ${amountUnitLabel(unit)} in ${fills} fill${fills !== 1 ? "s" : ""}`;
  }
  if (treatment.products.length === 0) return "-";
  const sorted = [...treatment.products].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  const first = sorted[0];
  if (sorted.length === 1) return `${first.rate_applied} ${rateUnitLabel(first.rate_unit)}`;
  return `${first.rate_applied} ${rateUnitLabel(first.rate_unit)} (+${sorted.length - 1})`;
}

export default async function TreatmentsPage() {
  const [treatments, products, equipment, profile] = await Promise.all([
    listTreatments().catch(() => []),
    listProducts().catch(() => []),
    listEquipment().catch(() => []),
    getLawnProfile().catch(() => null),
  ]);

  const productMap = Object.fromEntries(products.map((p) => [p.id, p]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Treatments</h1>
          <p className="text-sm text-muted-foreground">{treatments.length} log{treatments.length !== 1 ? "s" : ""}</p>
        </div>
        <NewTreatmentDialog
          products={products}
          equipment={equipment}
          defaultSqft={profile?.total_sqft}
        />
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Product</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Rate / mix</TableHead>
              <TableHead>Area (sq ft)</TableHead>
              <TableHead>Target</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {treatments.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  No treatments logged yet.
                </TableCell>
              </TableRow>
            )}
            {treatments.map((t) => (
              <TableRow key={t.id}>
                <TableCell>{formatDate(t.applied_at)}</TableCell>
                <TableCell className="font-medium">
                  {productSummary(t, productMap)}
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">
                    {t.application_method === "liquid" ? "liquid" : t.application_method}
                  </Badge>
                </TableCell>
                <TableCell>{rateSummary(t)}</TableCell>
                <TableCell>{t.area_treated_sqft.toLocaleString()}</TableCell>
                <TableCell>
                  {t.target ? <Badge variant="outline">{t.target}</Badge> : "–"}
                </TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/treatments/${t.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {treatments.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No treatments logged yet.</p>
        )}
        {treatments.map((t) => (
          <Link key={t.id} href={`/treatments/${t.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <FlaskConical className="h-5 w-5 shrink-0 text-emerald-600" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{productSummary(t, productMap)}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(t.applied_at)} · {rateSummary(t)}
                  </p>
                </div>
                {t.target && (
                  <Badge variant="outline" className="shrink-0 text-xs">{t.target}</Badge>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
