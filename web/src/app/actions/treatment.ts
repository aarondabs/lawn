"use server";

import { revalidatePath } from "next/cache";
import { createTreatment, patchTreatment, deleteTreatment, type Treatment } from "@/lib/api";

type TreatmentInput = Omit<Treatment, "id" | "created_at" | "updated_at">;

export async function addTreatment(
  data: TreatmentInput,
): Promise<{ ok: true; data: Treatment } | { ok: false; error: string }> {
  try {
    const result = await createTreatment(data);
    revalidatePath("/treatments");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to log treatment" };
  }
}

export async function updateTreatment(
  id: string,
  data: Partial<TreatmentInput>,
): Promise<{ ok: true; data: Treatment } | { ok: false; error: string }> {
  try {
    const result = await patchTreatment(id, data);
    revalidatePath("/treatments");
    revalidatePath(`/treatments/${id}`);
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update treatment" };
  }
}

export async function removeTreatment(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteTreatment(id);
    revalidatePath("/treatments");
    revalidatePath("/");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete treatment" };
  }
}
