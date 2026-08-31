/**
 * Drives the chat surface through actual submits — the Phase 2c lesson: API
 * tests alone once hid a form whose submit button silently did nothing.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/app/assistant/_components/chat-panel";
import { sendChatMessage } from "@/app/actions/assistant";

vi.mock("@/app/actions/assistant", () => ({
  sendChatMessage: vi.fn(),
  removeConversation: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const mockedSend = vi.mocked(sendChatMessage);

function renderPanel() {
  return render(<ChatPanel conversations={[]} active={null} showKind="chat" />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ChatPanel", () => {
  it("renders an existing conversation's transcript from props", () => {
    render(
      <ChatPanel
        conversations={[]}
        active={{
          id: "conv-9",
          kind: "chat",
          title: "Watering question",
          created_at: "2026-08-31T12:00:00Z",
          updated_at: "2026-08-31T12:01:00Z",
          messages: [
            { id: "m1", role: "user", content: "Should I water this week?", created_at: "2026-08-31T12:00:00Z" },
            { id: "m2", role: "assistant", content: "Yes — you are under budget.", created_at: "2026-08-31T12:01:00Z" },
          ],
        }}
        showKind="chat"
      />,
    );

    expect(screen.getByText("Should I water this week?")).toBeInTheDocument();
    expect(screen.getByText("Yes — you are under budget.")).toBeInTheDocument();
    expect(screen.getByText("Watering question")).toBeInTheDocument();
    // Nav links must carry visible labels — the Button asChild/render shim
    // once swallowed link children in this client component (Capture.PNG bug).
    expect(screen.getByRole("link", { name: /New/ })).toHaveAttribute("href", "/assistant");
    expect(screen.getByRole("link", { name: "Chats" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Briefings" })).toHaveAttribute(
      "href",
      "/assistant?kind=briefing",
    );
  });

  it("sends a typed message through the form and renders the reply", async () => {
    mockedSend.mockResolvedValue({
      ok: true,
      data: {
        conversation_id: "conv-1",
        reply: {
          id: "msg-2",
          role: "assistant",
          content: "Your last mow was 3 days ago.",
          created_at: "2026-08-31T12:00:00Z",
        },
        truncated: false,
      },
    });

    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByRole("textbox", { name: "Message" }), "When did I last mow?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(mockedSend).toHaveBeenCalledWith({ conversation_id: null, message: "When did I last mow?" });
    expect(await screen.findByText("Your last mow was 3 days ago.")).toBeInTheDocument();
    // The user's own message stays in the transcript.
    expect(screen.getByText("When did I last mow?")).toBeInTheDocument();
  });

  it("submits on Enter without a button click", async () => {
    mockedSend.mockResolvedValue({
      ok: true,
      data: {
        conversation_id: "conv-1",
        reply: { id: "m", role: "assistant", content: "Reply.", created_at: "2026-08-31T12:00:00Z" },
        truncated: false,
      },
    });

    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByRole("textbox", { name: "Message" }), "quick question{Enter}");

    expect(mockedSend).toHaveBeenCalledWith({ conversation_id: null, message: "quick question" });
    expect(await screen.findByText("Reply.")).toBeInTheDocument();
  });

  it("on failure shows the API's error, keeps the draft, and fabricates nothing", async () => {
    mockedSend.mockResolvedValue({
      ok: false,
      error: "assistant unavailable: could not reach the model API",
    });

    const user = userEvent.setup();
    renderPanel();

    const box = screen.getByRole("textbox", { name: "Message" });
    await user.type(box, "Doomed question");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "assistant unavailable: could not reach the model API",
    );
    // Draft preserved for retry; the failed exchange leaves no transcript bubbles.
    expect(box).toHaveValue("Doomed question");
    expect(screen.queryByText("Doomed question", { selector: "div" })).not.toBeInTheDocument();
  });

  it("flags a truncated answer instead of presenting it as complete", async () => {
    mockedSend.mockResolvedValue({
      ok: true,
      data: {
        conversation_id: "conv-1",
        reply: { id: "m", role: "assistant", content: "Partial…", created_at: "2026-08-31T12:00:00Z" },
        truncated: true,
      },
    });

    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByRole("textbox", { name: "Message" }), "long question{Enter}");

    expect(await screen.findByText(/hit the output limit/)).toBeInTheDocument();
  });
});
