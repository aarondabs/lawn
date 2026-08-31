import type { Metadata } from "next";

import { getAssistantConversation, listAssistantConversations } from "@/lib/api";
import { ChatPanel } from "./_components/chat-panel";

export const metadata: Metadata = { title: "Assistant" };

export default async function AssistantPage({
  searchParams,
}: {
  searchParams: Promise<{ c?: string; kind?: string }>;
}) {
  const { c, kind } = await searchParams;
  const showKind = kind === "briefing" ? "briefing" : "chat";
  const conversations = await listAssistantConversations(showKind).catch(() => []);
  const active = c ? await getAssistantConversation(c).catch(() => null) : null;

  return <ChatPanel conversations={conversations} active={active} showKind={showKind} />;
}
