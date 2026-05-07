"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Treatment, Product, Equipment } from "@/lib/api";
import { TreatmentForm } from "@/components/forms/treatment-form";
import { removeTreatment } from "@/app/actions/treatment";

type Props = { treatment: Treatment; products: Product[]; equipment: Equipment[] };

export function TreatmentDetailClient({ treatment, products, equipment }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm("Delete this treatment log? This cannot be undone.")) return;
    const result = await removeTreatment(treatment.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Treatment deleted.");
    router.push("/treatments");
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
          <DialogHeader><DialogTitle>Edit treatment</DialogTitle></DialogHeader>
          <TreatmentForm
            treatment={treatment}
            products={products}
            equipment={equipment}
            onSuccess={() => setEditOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
