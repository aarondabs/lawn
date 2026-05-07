"use server";

import { revalidatePath } from "next/cache";
import {
  createCulturalPractice,
  patchCulturalPractice,
  deleteCulturalPractice,
  type CulturalPractice,
} from "@/lib/api";

type CulturalInput = Omit<CulturalPractice, "id" | "created_at" | "updated_at">;

export async function addCulturalPractice(
  data: CulturalInput,
): Promise<{ ok: true; data: CulturalPractice } | { ok: false; error: string }> {
  try {
    const result = await createCulturalPractice(data);
    revalidatePath("/cultural");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to log cultural practice" };
  }
}

export async function updateCulturalPractice(
  id: string,
  data: Partial<CulturalInput>,
): Promise<{ ok: true; data: CulturalPractice } | { ok: false; error: string }> {
  try {
    const result = await patchCulturalPractice(id, data);
    revalidatePath("/cultural");
    revalidatePath(`/cultural/${id}`);
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update cultural practice" };
  }
}

export async function removeCulturalPractice(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteCulturalPractice(id);
    revalidatePath("/cultural");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete cultural practice" };
  }
}
