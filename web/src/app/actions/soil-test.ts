"use server";

import { revalidatePath } from "next/cache";
import { createSoilTest, patchSoilTest, deleteSoilTest, type SoilTest } from "@/lib/api";

type SoilTestInput = Omit<SoilTest, "id" | "created_at" | "updated_at">;

export async function addSoilTest(
  data: SoilTestInput,
): Promise<{ ok: true; data: SoilTest } | { ok: false; error: string }> {
  try {
    const result = await createSoilTest(data);
    revalidatePath("/soil-tests");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to save soil test" };
  }
}

export async function updateSoilTest(
  id: string,
  data: Partial<SoilTestInput>,
): Promise<{ ok: true; data: SoilTest } | { ok: false; error: string }> {
  try {
    const result = await patchSoilTest(id, data);
    revalidatePath("/soil-tests");
    revalidatePath(`/soil-tests/${id}`);
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update soil test" };
  }
}

export async function removeSoilTest(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteSoilTest(id);
    revalidatePath("/soil-tests");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete soil test" };
  }
}
