"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TreatmentForm } from "@/components/forms/treatment-form";
import type { Product, Equipment, Treatment } from "@/lib/api";

export type QuickLogData = {
  products: Product[];
  equipment: Equipment[];
  lastTreatment: Treatment | null;
  defaultSqft: number | null;
};

export function QuickLogFab() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<QuickLogData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    if (isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/quick-log-data", {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Quick log request failed with status ${response.status}`);
      }

      const payload = (await response.json()) as QuickLogData;
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load quick log defaults.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen && !data && !isLoading) {
      void loadData();
    }
  }

  const { products, equipment, lastTreatment, defaultSqft } = data ?? {
    products: [],
    equipment: [],
    lastTreatment: null,
    defaultSqft: null,
  };

  // Prefill from last treatment — date resets to now, everything else carries over.
  const prefill = lastTreatment
    ? { ...lastTreatment, applied_at: new Date().toISOString() }
    : undefined;

  return (
    <>
      {/* FAB sits above the two-row mobile bottom nav. */}
      <button
        onClick={() => handleOpenChange(true)}
        aria-label="Quick log treatment"
        className="fixed right-4 bottom-28 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform active:scale-95 md:bottom-6"
      >
        <Plus className="h-6 w-6" />
      </button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Quick log treatment</DialogTitle>
          </DialogHeader>
          {isLoading && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
              </div>
              <Skeleton className="h-24" />
              <Skeleton className="h-8 w-32" />
            </div>
          )}
          {!isLoading && error && (
            <div className="space-y-3 rounded-lg border border-destructive/20 bg-destructive/5 p-4">
              <p className="text-sm font-medium text-destructive">Quick log is unavailable right now.</p>
              <p className="text-sm text-muted-foreground">{error}</p>
              <Button type="button" variant="outline" onClick={() => void loadData()}>
                Retry
              </Button>
            </div>
          )}
          {!isLoading && !error && data && (
            <TreatmentForm
              treatment={prefill}
              products={products}
              equipment={equipment}
              defaultSqft={defaultSqft ?? undefined}
              onSuccess={() => setOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
