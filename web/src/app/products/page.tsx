import type { Metadata } from "next";
import Link from "next/link";
import { Plus, Sprout } from "lucide-react";

import { listProducts } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { amountUnitLabel, rateUnitLabel } from "@/lib/enums";

export const metadata: Metadata = { title: "Products" };

export default async function ProductsPage() {
  const products = await listProducts().catch(() => []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Products</h1>
          <p className="text-sm text-muted-foreground">{products.length} product{products.length !== 1 ? "s" : ""}</p>
        </div>
        <Button asChild size="sm">
          <Link href="/products/new"><Plus className="mr-1 h-4 w-4" />Add</Link>
        </Button>
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Manufacturer</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Label rate</TableHead>
              <TableHead>Inventory</TableHead>
              <TableHead>Apps left</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">No products yet.</TableCell>
              </TableRow>
            )}
            {products.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium">{p.name}</TableCell>
                <TableCell>{p.manufacturer}</TableCell>
                <TableCell><Badge variant="outline">{p.product_type.replace(/_/g, " ")}</Badge></TableCell>
                <TableCell>{p.label_rate} {rateUnitLabel(p.label_rate_unit)}</TableCell>
                <TableCell>
                  {p.current_inventory != null ? (
                    <span className={p.current_inventory < 0 ? "font-medium text-destructive" : undefined}>
                      {p.current_inventory} {amountUnitLabel(p.current_inventory_unit ?? "")}
                    </span>
                  ) : (
                    "–"
                  )}
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {p.applications_remaining != null ? `~${p.applications_remaining.toFixed(1)}` : "–"}
                </TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/products/${p.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {products.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No products yet.</p>
        )}
        {products.map((p) => (
          <Link key={p.id} href={`/products/${p.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <Sprout className="h-5 w-5 shrink-0 text-green-600" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.name}</p>
                  <p className="text-xs text-muted-foreground">{p.manufacturer} · {p.product_type.replace(/_/g, " ")}</p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {p.label_rate} {rateUnitLabel(p.label_rate_unit)}
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
