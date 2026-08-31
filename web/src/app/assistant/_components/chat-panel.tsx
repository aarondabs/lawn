"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Loader2, MessageCirclePlus, Send, Sparkles, Trash2 } from "lucide-react";

import { sendChatMessage, removeConversation } from "@/app/actions/assistant";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type {
  AssistantConversation,
  AssistantConversationKind,
  AssistantConversationSummary,
  AssistantMessage,
} from "@/lib/api";

type ChatPanelProps = {
  conversations: AssistantConversationSummary[];
  active: AssistantConversation | null;
  showKind: AssistantConversationKind;
};

/** Minimal inline rendering: the assistant is prompted for plain prose but
 * still bolds key figures. Everything else renders as literal text. */
function renderInline(text: string) {
  return text
    .split(/\*\*(.+?)\*\*/g)
    .map((part, i) => (i % 2 === 1 ? <strong key={i}>{part}</strong> : part));
}

function formatTimestamp(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    timeZone: "America/Chicago",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ChatPanel({ conversations, active, showKind }: ChatPanelProps) {
  const router = useRouter();
  const [conversationId, setConversationId] = useState<string | null>(active?.id ?? null);
  const [messages, setMessages] = useState<AssistantMessage[]>(active?.messages ?? []);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [truncated, setTruncated] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, sending]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setError(null);
    setTruncated(false);
    setInput("");
    setMessages((m) => [
      ...m,
      { id: crypto.randomUUID(), role: "user", content: text, created_at: new Date().toISOString() },
    ]);

    const result = await sendChatMessage({ conversation_id: conversationId, message: text });
    if (result.ok) {
      setConversationId(result.data.conversation_id);
      setMessages((m) => [...m, result.data.reply]);
      setTruncated(result.data.truncated);
      if (!conversationId) {
        window.history.replaceState(null, "", `/assistant?c=${result.data.conversation_id}`);
      }
    } else {
      // Honest failure: drop the optimistic bubble, put the text back in the
      // input, and show the API's own error. Never a made-up reply.
      setMessages((m) => m.slice(0, -1));
      setInput(text);
      setError(result.error);
    }
    setSending(false);
  }

  async function handleDelete(id: string) {
    const result = await removeConversation(id);
    if (result.ok) {
      if (id === conversationId) {
        router.push("/assistant");
      } else {
        router.refresh();
      }
    } else {
      setError(result.error);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Sparkles className="h-5 w-5 text-emerald-600" />
            Assistant
          </h1>
          <p className="truncate text-sm text-muted-foreground">
            {active?.title ?? "Read-only: it answers and recommends; you log."}
          </p>
        </div>
        {/* Styled Links, not <Button asChild>: the asChild/render shim drops
            the link's children when used from a client component here. */}
        <Link href="/assistant" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          <MessageCirclePlus className="mr-1 h-4 w-4" />
          New
        </Link>
      </div>

      <Card>
        <CardContent className="space-y-4 py-4">
          {messages.length === 0 && !sending && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Ask about your lawn — treatments, watering, products, timing. Answers are grounded
              in your logged data.
            </p>
          )}

          {messages.map((m) => (
            <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm",
                  m.role === "user" ? "bg-secondary text-secondary-foreground" : "bg-muted",
                )}
              >
                {m.role === "assistant" ? renderInline(m.content) : m.content}
                <div className="mt-1 text-[10px] text-muted-foreground">{formatTimestamp(m.created_at)}</div>
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Thinking…
              </div>
            </div>
          )}

          {truncated && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              The answer hit the output limit and may be cut off.
            </p>
          )}

          {error && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
            className="flex items-end gap-2"
          >
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              placeholder="Ask the assistant…"
              rows={2}
              className="min-h-0 flex-1 resize-none"
              disabled={sending}
              aria-label="Message"
            />
            <Button type="submit" size="icon" disabled={sending || !input.trim()} aria-label="Send">
              <Send className="h-4 w-4" />
            </Button>
          </form>
          <div ref={endRef} />
        </CardContent>
      </Card>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-muted-foreground">Recent</h2>
          <div className="flex gap-1">
            <Link
              href="/assistant"
              className={cn(buttonVariants({ variant: showKind === "chat" ? "secondary" : "ghost", size: "sm" }))}
            >
              Chats
            </Link>
            <Link
              href="/assistant?kind=briefing"
              className={cn(
                buttonVariants({ variant: showKind === "briefing" ? "secondary" : "ghost", size: "sm" }),
              )}
            >
              Briefings
            </Link>
          </div>
        </div>

        {conversations.length === 0 && (
          <p className="text-sm text-muted-foreground">
            {showKind === "briefing" ? "No briefings yet." : "No conversations yet."}
          </p>
        )}

        {conversations.map((c) => (
          <div
            key={c.id}
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-2",
              c.id === conversationId && "border-emerald-600/50 bg-muted/50",
            )}
          >
            <Link href={`/assistant?c=${c.id}`} className="min-w-0 flex-1">
              <p className="truncate text-sm">{c.title ?? "Untitled"}</p>
              <p className="text-xs text-muted-foreground">{formatTimestamp(c.updated_at)}</p>
            </Link>
            {c.kind === "briefing" && (
              <Badge variant="outline" className="shrink-0 text-xs">
                briefing
              </Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Delete conversation ${c.title ?? c.id}`}
              onClick={() => void handleDelete(c.id)}
            >
              <Trash2 className="h-4 w-4 text-muted-foreground" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
