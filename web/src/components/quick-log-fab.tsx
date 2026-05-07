"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { TreatmentForm } from "@/components/forms/treatment-form";
import type { Product, Equipment, Treatment } from "@/lib/api";

export type QuickLogData = {
  products: Product[];
  equipment: Equipment[];
  lastTreatment: Treatment | null;
  defaultSqft: number | null;
};

type Props = { data: QuickLogData };

export function QuickLogFab({ data }: Props) {
  const [open, setOpen] = useState(false);

  const { products, equipment, lastTreatment, defaultSqft } = data;

  // Prefill from last treatment — date resets to now, everything else carries over.
  const prefill = lastTreatment
    ? { ...lastTreatment, applied_at: new Date().toISOString() }
    : undefined;

  return (
    <>
      {/* FAB sits above the mobile bottom nav (pb-20 in main) */}
      <button
        onClick={() => setOpen(true)}
        aria-label="Quick log treatment"
        className="fixed bottom-20 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform active:scale-95 md:bottom-6"
      >
        <Plus className="h-6 w-6" />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Quick log treatment</DialogTitle>
          </DialogHeader>
          <TreatmentForm
            treatment={prefill}
            products={products}
            equipment={equipment}
            defaultSqft={defaultSqft ?? undefined}
            onSuccess={() => setOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
