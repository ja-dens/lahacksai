"""Normalize application-owned events, not vendor webhook payloads."""
import base64;
import hashlib;
import json;
import from datetime { datetime, timezone }

def canonical(value: any) -> str {
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"));
}

def digest(value: any) -> str {
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest();
}

def utc_time(value: str) -> str {
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"));
    if parsed.tzinfo is None {
        raise ValueError("sent_at requires a timezone");
    }
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds");
}

def now -> str {
    return datetime.now(timezone.utc).isoformat(timespec="microseconds");
}

def normalize_event(raw: dict) -> dict {
    for field in ["platform", "conversation_id", "message_id", "sender_id", "sent_at"] {
        if not isinstance(raw.get(field), str) or not raw[field].strip() {
            raise ValueError("Missing or invalid field: " + field);
        }
    }
    text = raw.get("text");
    if text is not None and not isinstance(text, str) {
        raise ValueError("text must be a string or null");
    }
    assistant = raw.get("from_assistant", False);
    if not isinstance(assistant, bool) {
        raise ValueError("from_assistant must be boolean");
    }
    kind = raw.get("kind", "sticker" if raw.get("sticker") else "text");
    if kind not in ["text", "sticker", "image", "audio", "other"] {
        raise ValueError("Unknown message kind");
    }
    media = raw.get("sticker");
    if media is not None {
        if kind != "sticker" or not isinstance(media, dict) {
            raise ValueError("Sticker media requires an explicit sticker event");
        }
        encoded = media.get("data_base64", "");
        if not isinstance(encoded, str) { raise ValueError("Sticker data must be base64 text"); }
        data = base64.b64decode(str(encoded), validate=True);
        if not data or len(data) > 5000000 {
            raise ValueError("Sticker bytes must be present and at most 5 MB");
        }
        mime = media.get("mime_type");
        if not isinstance(mime, str) {
            raise ValueError("Sticker MIME type is required");
        }
        if media.get("sha256") is not None and media["sha256"] != hashlib.sha256(data).hexdigest() {
            raise ValueError("Sticker hash mismatch");
        }
        media = {
            "data_base64": base64.b64encode(data).decode("ascii"),
            "mime_type": mime,
            "sha256": hashlib.sha256(data).hexdigest()
        };
    }
    reply = raw.get("reply_to_message_id");
    if reply is not None and not isinstance(reply, str) {
        raise ValueError("reply_to_message_id must be a string or null");
    }
    return {
        "platform": raw["platform"], "conversation_id": raw["conversation_id"],
        "message_id": raw["message_id"], "sender_id": raw["sender_id"],
        "sent_at": utc_time(str(raw["sent_at"])), "from_assistant": assistant,
        "text": text, "kind": kind, "sticker": media,
        "reply_to_message_id": reply
    };
}

def supported_sticker(event: dict) -> bool {
    media = event.get("sticker");
    if not media or media["mime_type"] != "image/png" { return False; }
    data = base64.b64decode(media["data_base64"]);
    return data.startswith(b"\x89PNG\r\n\x1a\n");
}
