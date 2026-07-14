"""
services/conversation_memory.py
--------------------------------
Gives the reply-writing agent memory of the ENTIRE email thread, not just the
single latest message.

Without this, every reply is generated in isolation and the AI can:
  - ask the customer for info they already gave two messages ago
  - contradict something it (or a human) already promised
  - lose track of what stage a conversation is at (e.g. already offered a refund)

`ConversationMemory.build_context()` fetches the full Gmail thread, labels each
message as the Customer or the Business, trims it to a safe size, and returns
a plain-text block that gets injected into the AI prompt.
"""

from app.mcp.gmail import get_thread_messages, get_own_email_address

MAX_MESSAGES = 6             # how many prior messages to include (most recent N)
MAX_CHARS_PER_MESSAGE = 500  # truncate very long emails so the prompt stays small


class ConversationMemory:

    def build_context(
        self,
        business_id: int,
        thread_id: str,
        exclude_message_id: str = None,
    ) -> dict:
        """
        Returns:
            {
                "history_text": "<formatted conversation for the prompt, or '' if none>",
                "message_count": <int, prior messages found>,
                "messages": [ ...parsed messages, oldest -> newest... ]
            }
        Never raises: if the thread can't be fetched (deleted, permissions, single
        message thread, etc.) it degrades gracefully to "no history".
        """
        if not thread_id:
            return {"history_text": "", "message_count": 0, "messages": []}

        try:
            messages = get_thread_messages(business_id, thread_id)
            own_address = get_own_email_address(business_id)
        except Exception as exc:
            print(f"[ConversationMemory] Could not fetch thread {thread_id}: {exc}")
            return {"history_text": "", "message_count": 0, "messages": []}

        if exclude_message_id:
            messages = [m for m in messages if m["id"] != exclude_message_id]

        if not messages:
            return {"history_text": "", "message_count": 0, "messages": []}

        # Keep only the most recent N so the prompt doesn't blow up on long threads
        trimmed = messages[-MAX_MESSAGES:]

        lines = []
        for m in trimmed:
            speaker = "Business" if m.get("from_email", "").lower() == own_address else "Customer"
            body = (m.get("body") or m.get("snippet") or "").strip()
            if len(body) > MAX_CHARS_PER_MESSAGE:
                body = body[:MAX_CHARS_PER_MESSAGE].rstrip() + "…"
            lines.append(f"{speaker} ({m.get('date', 'unknown date')}):\n{body}")

        history_text = "\n\n".join(lines)

        return {
            "history_text": history_text,
            "message_count": len(messages),
            "messages": trimmed,
        }
