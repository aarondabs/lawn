"use server";

import { revalidatePath } from "next/cache";
import {
  createReminder,
  patchReminder,
  completeReminder,
  snoozeReminder,
  deleteReminder,
  type Reminder,
  type ReminderInput,
} from "@/lib/api";

export async function addReminder(
  data: ReminderInput,
): Promise<{ ok: true; data: Reminder } | { ok: false; error: string }> {
  try {
    const result = await createReminder(data);
    revalidatePath("/reminders");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to create reminder" };
  }
}

export async function updateReminder(
  id: string,
  data: Partial<ReminderInput>,
): Promise<{ ok: true; data: Reminder } | { ok: false; error: string }> {
  try {
    const result = await patchReminder(id, data);
    revalidatePath("/reminders");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update reminder" };
  }
}

export async function markReminderComplete(
  id: string,
  opts?: { completed_treatment_id?: string; completed_cultural_id?: string },
): Promise<{ ok: true; data: Reminder } | { ok: false; error: string }> {
  try {
    const result = await completeReminder(id, opts);
    revalidatePath("/reminders");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to complete reminder" };
  }
}

export async function snoozeReminderTo(
  id: string,
  new_due_date: string,
): Promise<{ ok: true; data: Reminder } | { ok: false; error: string }> {
  try {
    const result = await snoozeReminder(id, new_due_date);
    revalidatePath("/reminders");
    revalidatePath("/");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to snooze reminder" };
  }
}

export async function removeReminder(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteReminder(id);
    revalidatePath("/reminders");
    revalidatePath("/");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete reminder" };
  }
}
