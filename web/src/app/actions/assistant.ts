"use server";

import { revalidatePath } from "next/cache";
import {
  ApiError,
  deleteAssistantConversation,
  sendAssistantChat,
  type AssistantChatResponse,
} from "@/lib/api";

function errorMessage(err: unknown): string {
  // The API's 503 detail is operator-honest ("assistant unavailable: ...",
  // "assistant not configured: ..."). Surface it verbatim; never invent a reply.
  if (err instanceof ApiError && typeof err.payload === "object" && err.payload !== null) {
    const detail = (err.payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return err instanceof Error ? err.message : "Assistant request failed";
}

export async function sendChatMessage(data: {
  conversation_id?: string | null;
  message: string;
}): Promise<{ ok: true; data: AssistantChatResponse } | { ok: false; error: string }> {
  try {
    const result = await sendAssistantChat(data);
    revalidatePath("/assistant");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: errorMessage(err) };
  }
}

export async function removeConversation(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteAssistantConversation(id);
    revalidatePath("/assistant");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: errorMessage(err) };
  }
}
