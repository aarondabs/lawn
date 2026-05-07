"use server";

import { revalidatePath } from "next/cache";
import { createEquipment, patchEquipment, deleteEquipment, type Equipment } from "@/lib/api";

type EquipmentInput = Omit<Equipment, "id" | "created_at" | "updated_at">;

export async function addEquipment(
  data: EquipmentInput,
): Promise<{ ok: true; data: Equipment } | { ok: false; error: string }> {
  try {
    const result = await createEquipment(data);
    revalidatePath("/equipment");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to create equipment" };
  }
}

export async function updateEquipment(
  id: string,
  data: Partial<EquipmentInput>,
): Promise<{ ok: true; data: Equipment } | { ok: false; error: string }> {
  try {
    const result = await patchEquipment(id, data);
    revalidatePath("/equipment");
    revalidatePath(`/equipment/${id}`);
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update equipment" };
  }
}

export async function removeEquipment(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteEquipment(id);
    revalidatePath("/equipment");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete equipment" };
  }
}
