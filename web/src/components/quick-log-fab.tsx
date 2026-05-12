"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CulturalPracticeForm } from "@/components/forms/cultural-practice-form";
import { EquipmentForm } from "@/components/forms/equipment-form";
import { IrrigationZoneForm } from "@/components/forms/irrigation-zone-form";
import { LawnProfileForm } from "@/components/forms/lawn-profile-form";
import { ProductForm } from "@/components/forms/product-form";
import { SoilTestForm } from "@/components/forms/soil-test-form";
import { TreatmentForm } from "@/components/forms/treatment-form";
import type { Product, Equipment, LawnProfile, Treatment } from "@/lib/api";

type QuickLogAction =
  | "cultural"
  | "equipment"
  | "lawn-profile"
  | "product"
  | "soil-test"
  | "treatment"
  | "zone";

export type QuickLogData = {
  products: Product[];
  equipment: Equipment[];
  profile: LawnProfile | null;
  lastTreatment: Treatment | null;
  defaultSqft: number | null;
};

const FAB_HIDDEN_PATHS = ["/reminders"];

function actionForPath(pathname: string): QuickLogAction {
  if (pathname.startsWith("/cultural")) {
    return "cultural";
  }
  if (pathname.startsWith("/equipment")) {
    return "equipment";
  }
  if (pathname.startsWith("/products")) {
    return "product";
  }
  if (pathname.startsWith("/soil-tests")) {
    return "soil-test";
  }
  if (pathname.startsWith("/zones")) {
    return "zone";
  }
  if (pathname.startsWith("/settings")) {
    return "lawn-profile";
  }
  if (pathname.startsWith("/treatments")) {
    return "treatment";
  }

  return "cultural";
}

function titleForAction(action: QuickLogAction) {
  switch (action) {
    case "cultural":
      return "Quick log cultural practice";
    case "equipment":
      return "Quick add equipment";
    case "lawn-profile":
      return "Quick update lawn profile";
    case "product":
      return "Quick add product";
    case "soil-test":
      return "Quick add soil test";
    case "zone":
      return "Quick add irrigation zone";
    case "treatment":
    default:
      return "Quick log treatment";
  }
}

export function QuickLogFab() {
  const pathname = usePathname();
  const action = actionForPath(pathname);
  const hidden = FAB_HIDDEN_PATHS.some((p) => pathname.startsWith(p));

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

  const { products, equipment, profile, lastTreatment, defaultSqft } = data ?? {
    products: [],
    equipment: [],
    profile: null,
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
      {!hidden && (
      <button
        onClick={() => handleOpenChange(true)}
        aria-label={titleForAction(action)}
        className="fixed right-4 bottom-28 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform active:scale-95 md:bottom-6"
      >
        <Plus className="h-6 w-6" />
      </button>
      )}

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{titleForAction(action)}</DialogTitle>
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
          {!isLoading && !error && data && action === "treatment" && (
            <TreatmentForm
              treatment={prefill}
              products={products}
              equipment={equipment}
              defaultSqft={defaultSqft ?? undefined}
              onSuccess={() => setOpen(false)}
            />
          )}
          {!isLoading && !error && data && action === "cultural" && (
            <CulturalPracticeForm
              equipment={equipment}
              initialPracticeType="mow"
              onSuccess={() => setOpen(false)}
            />
          )}
          {!isLoading && !error && data && action === "equipment" && (
            <EquipmentForm onSuccess={() => setOpen(false)} />
          )}
          {!isLoading && !error && data && action === "product" && (
            <ProductForm onSuccess={() => setOpen(false)} />
          )}
          {!isLoading && !error && data && action === "soil-test" && (
            <SoilTestForm onSuccess={() => setOpen(false)} />
          )}
          {!isLoading && !error && data && action === "zone" && (
            <IrrigationZoneForm onSuccess={() => setOpen(false)} />
          )}
          {!isLoading && !error && data && action === "lawn-profile" && (
            <LawnProfileForm defaultValues={profile ?? undefined} />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
