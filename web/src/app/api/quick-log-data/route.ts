import { NextResponse } from "next/server";

import {
  getLawnProfile,
  listEquipment,
  listProducts,
  listTreatments,
} from "@/lib/api";
import type { QuickLogData } from "@/components/quick-log-fab";

export async function GET() {
  const [products, equipment, treatments, profile] = await Promise.all([
    listProducts().catch(() => []),
    listEquipment().catch(() => []),
    listTreatments().catch(() => []),
    getLawnProfile().catch(() => null),
  ]);

  const sortedTreatments = [...treatments].sort((a, b) => b.applied_at.localeCompare(a.applied_at));
  const payload: QuickLogData = {
    products,
    equipment,
    profile,
    lastTreatment: sortedTreatments[0] ?? null,
    defaultSqft: profile?.total_sqft ?? null,
  };

  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}