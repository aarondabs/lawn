"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Product } from "@/lib/api";
import { ProductForm } from "@/components/forms/product-form";
import { removeProduct } from "@/app/actions/product";

type Props = { product: Product };

export function ProductDetailClient({ product }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete "${product.name}"? This cannot be undone.`)) return;
    const result = await removeProduct(product.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Product deleted.");
    router.push("/products");
  }

  return (
    <>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
          <Pencil className="mr-1 h-3 w-3" /> Edit
        </Button>
        <Button variant="destructive" size="sm" onClick={handleDelete}>Delete</Button>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader><DialogTitle>Edit product</DialogTitle></DialogHeader>
          <ProductForm product={product} onSuccess={() => setEditOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
