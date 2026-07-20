import { NextResponse } from "next/server";

import {
  getLawnProfile,
  listCulturalPractices,
  listEquipment,
  listProducts,
  listTreatments,
} from "@/lib/api";
import { defaultCutHeight } from "@/lib/enums";
import type { QuickLogData } from "@/components/quick-log-fab";

export async function GET() {
  const [products, equipment, treatments, practices, profile] = await Promise.all([
    listProducts().catch(() => []),
    listEquipment().catch(() => []),
    listTreatments().catch(() => []),
    listCulturalPractices().catch(() => []),
    getLawnProfile().catch(() => null),
  ]);

  const sortedTreatments = [...treatments].sort((a, b) => b.applied_at.localeCompare(a.applied_at));
  const payload: QuickLogData = {
    products,
    equipment,
    profile,
    lastTreatment: sortedTreatments[0] ?? null,
    defaultSqft: profile?.total_sqft ?? null,
    defaultCutHeight: defaultCutHeight(practices, profile?.target_mow_height_inches) ?? null,
  };

  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}