import type { Metadata } from "next";
import Link from "next/link";
import { FlaskConical } from "lucide-react";

import { listTreatments, listProducts, listEquipment } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { NewTreatmentDialog } from "./_components/new-treatment-dialog";

export const metadata: Metadata = { title: "Treatments" };

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default async function TreatmentsPage() {
  const [treatments, products, equipment] = await Promise.all([
    listTreatments().catch(() => []),
    listProducts().catch(() => []),
    listEquipment().catch(() => []),
  ]);

  const productMap = Object.fromEntries(products.map((p) => [p.id, p]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Treatments</h1>
          <p className="text-sm text-muted-foreground">{treatments.length} log{treatments.length !== 1 ? "s" : ""}</p>
        </div>
        <NewTreatmentDialog products={products} equipment={equipment} />
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Product</TableHead>
              <TableHead>Rate</TableHead>
              <TableHead>Area (sq ft)</TableHead>
              <TableHead>Target</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {treatments.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No treatments logged yet.
                </TableCell>
              </TableRow>
            )}
            {treatments.map((t) => (
              <TableRow key={t.id}>
                <TableCell>{formatDate(t.applied_at)}</TableCell>
                <TableCell className="font-medium">
                  {productMap[t.product_id]?.name ?? "Unknown product"}
                </TableCell>
                <TableCell>{t.rate_applied} {t.rate_unit}</TableCell>
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
                  <p className="truncate font-medium">{productMap[t.product_id]?.name ?? "Unknown"}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(t.applied_at)} · {t.rate_applied} {t.rate_unit}
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
