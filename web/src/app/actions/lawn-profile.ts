"use server";

import { revalidatePath } from "next/cache";
import { upsertLawnProfile, patchLawnProfile, type LawnProfile } from "@/lib/api";

export async function saveLawnProfile(
  data: Omit<LawnProfile, "id" | "created_at" | "updated_at">,
): Promise<{ ok: true; data: LawnProfile } | { ok: false; error: string }> {
  try {
    const result = await upsertLawnProfile(data);
    revalidatePath("/settings");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to save lawn profile" };
  }
}

export async function updateLawnProfile(
  data: Partial<Omit<LawnProfile, "id" | "created_at" | "updated_at">>,
): Promise<{ ok: true; data: LawnProfile } | { ok: false; error: string }> {
  try {
    const result = await patchLawnProfile(data);
    revalidatePath("/settings");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update lawn profile" };
  }
}
