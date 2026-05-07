import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProductForm } from "@/components/forms/product-form";

export const metadata: Metadata = { title: "New Product" };

export default function NewProductPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/products"><ArrowLeft className="mr-1 h-4 w-4" />Products</Link>
        </Button>
      </div>
      <div>
        <h1 className="text-2xl font-semibold">Add product</h1>
      </div>
      <Card className="max-w-2xl">
        <CardHeader><CardTitle className="text-base">Product details</CardTitle></CardHeader>
        <CardContent>
          <ProductForm />
        </CardContent>
      </Card>
    </div>
  );
}
