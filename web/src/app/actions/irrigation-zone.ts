"use server";

import { revalidatePath } from "next/cache";
import {
  createIrrigationZone,
  patchIrrigationZone,
  deleteIrrigationZone,
  type IrrigationZone,
} from "@/lib/api";

type ZoneInput = Omit<IrrigationZone, "id" | "created_at" | "updated_at">;

export async function addIrrigationZone(
  data: ZoneInput,
): Promise<{ ok: true; data: IrrigationZone } | { ok: false; error: string }> {
  try {
    const result = await createIrrigationZone(data);
    revalidatePath("/zones");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to create zone" };
  }
}

export async function updateIrrigationZone(
  id: string,
  data: Partial<ZoneInput>,
): Promise<{ ok: true; data: IrrigationZone } | { ok: false; error: string }> {
  try {
    const result = await patchIrrigationZone(id, data);
    revalidatePath("/zones");
    revalidatePath(`/zones/${id}`);
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update zone" };
  }
}

export async function removeIrrigationZone(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteIrrigationZone(id);
    revalidatePath("/zones");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete zone" };
  }
}
