"""Select the preceding message window and freeze its user context."""
import from .repository { preceding_messages, user_context }
import from sqlite3 { Connection }

def clip_text(text: str | None, maximum: int) -> tuple[str | None, bool] {
    if text is None { return (None, False); }
    return (text[:maximum], len(text) > maximum);
}

def build_request(db: Connection, target: dict, event: dict, recipient: str,
                  limit: int = 25, text_budget: int = 24000,
                  message_limit: int = 4000, target_limit: int = 4000) -> dict {
    if limit < 20 or limit > 25 { raise ValueError("Context limit must be 20–25"); }
    if text_budget < 1 { raise ValueError("Text budget must be positive"); }
    recent = preceding_messages(db, target, limit);
    remaining = text_budget;
    messages = [];
    # Spend the text budget on the most recent messages first, then restore order.
    for message in reversed(recent) {
        original = str(message["text"]) if message["text"] is not None else None;
        (text, truncated) = clip_text(original, min(message_limit, remaining));
        if text is not None { remaining -= len(text); }
        messages.append({
            "message_id": message["message_id"], "sender_id": message["sender_id"],
            "sent_at": message["sent_at"], "text": text,
            "text_truncated": truncated, "kind": message["kind"],
            "media_not_interpreted": message["kind"] not in ["text"],
            "reply_to_message_id": message["reply_to_message_id"]
        });
    }
    messages.reverse();
    original_target = str(event["text"]) if event["text"] is not None else None;
    (target_text, target_truncated) = clip_text(original_target, target_limit);
    return {
        "schema_version": 2, "policy_version": "context-v1",
        "source_message_id": event["message_id"],
        "platform": event["platform"], "conversation_id": event["conversation_id"],
        "sender_id": event["sender_id"], "recipient_id": recipient,
        "sent_at": event["sent_at"], "target_text": target_text,
        "target_text_truncated": target_truncated,
        "reply_to_message_id": event["reply_to_message_id"],
        "sticker": event["sticker"], "recent_messages": messages,
        "context_message_limit": limit, "context_text_character_budget": text_budget,
        "context_age_limit": None,
        "user_context": user_context(db, event, recipient)
    };
}
