import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { getProduct } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProductDetailClient } from "../_components/product-detail-client";
import { amountUnitLabel, rateUnitLabel } from "@/lib/enums";

export const metadata: Metadata = { title: "Product Detail" };

function DetailRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value ?? "–"}</p>
    </div>
  );
}

export default async function ProductDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let product;
  try {
    product = await getProduct(id);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/products"><ArrowLeft className="mr-1 h-4 w-4" />Products</Link>
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{product.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="outline">{product.product_type.replace(/_/g, " ")}</Badge>
            <span className="text-sm text-muted-foreground">{product.manufacturer}</span>
          </div>
        </div>
        <ProductDetailClient product={product} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Application</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-3">
            <DetailRow label="Label rate" value={`${product.label_rate} ${rateUnitLabel(product.label_rate_unit)}`} />
            <DetailRow label="Re-entry interval" value={product.reentry_interval_hours != null ? `${product.reentry_interval_hours} hrs` : null} />
            <DetailRow label="Min reapplication" value={product.min_reapplication_days != null ? `${product.min_reapplication_days} days` : null} />
            <DetailRow
              label="Max annual rate"
              value={product.max_annual_rate != null ? `${product.max_annual_rate} ${rateUnitLabel(product.max_annual_rate_unit ?? "")}` : null}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Inventory</CardTitle></CardHeader>
          <CardContent>
            {product.current_inventory != null ? (
              <>
                <p
                  className={`text-2xl font-semibold ${
                    product.current_inventory < 0 ? "text-destructive" : ""
                  }`}
                >
                  {product.current_inventory}{" "}
                  <span className="text-base font-normal text-muted-foreground">
                    {amountUnitLabel(product.current_inventory_unit ?? "")}
                  </span>
                </p>
                {product.current_inventory < 0 && (
                  <p className="mt-2 text-sm text-destructive">
                    Negative stock — a restock probably went unlogged. Treatments are never blocked
                    on inventory, so this just needs reconciling.
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Not tracked</p>
            )}
          </CardContent>
        </Card>
        {product.notes && (
          <Card className="sm:col-span-2">
            <CardHeader><CardTitle className="text-base">Notes</CardTitle></CardHeader>
            <CardContent><p className="text-sm whitespace-pre-wrap">{product.notes}</p></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
