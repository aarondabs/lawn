"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Product, Equipment, Treatment } from "@/lib/api";
import { TreatmentForm } from "@/components/forms/treatment-form";

type Props = {
  products: Product[];
  equipment: Equipment[];
  lastTreatment?: Treatment;
  defaultSqft?: number;
};

export function NewTreatmentDialog({ products, equipment, lastTreatment, defaultSqft }: Props) {
  const [open, setOpen] = useState(false);

  // Prefill from last treatment — but clear date (default to now) and id-linked fields stay
  const prefill = lastTreatment
    ? {
        ...lastTreatment,
        // Reset id so TreatmentForm treats it as a new record
        id: undefined as unknown as string,
        applied_at: new Date().toISOString(),
      }
    : undefined;

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-1 h-4 w-4" />Log
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader><DialogTitle>Log treatment</DialogTitle></DialogHeader>
          <TreatmentForm
            treatment={prefill}
            products={products}
            equipment={equipment}
            defaultSqft={defaultSqft}
            onSuccess={() => setOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
