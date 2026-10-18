"""One-call orchestration and the v2 candidate policy. No transport or database."""

from copy import deepcopy
from datetime import datetime
from typing import Any


def required_text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Invalid " + label)
    return value


def checked_timestamp(value: Any) -> str:
    text = required_text(value, "timestamp", 64)
    timestamp = datetime.fromisoformat(text)
    if timestamp.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone.")
    return text


def optional_text(value: Any, limit: int) -> str | None:
    if value is not None and (not isinstance(value, str) or len(value) > limit):
        raise ValueError("Invalid or oversized text.")
    return value


def model_context(request: dict) -> dict:
    if type(request.get("schema_version")) is not int or request["schema_version"] != 2:
        raise ValueError("Expected a v2 interpretation request.")
    for field in ["policy_version", "source_message_id", "platform", "conversation_id", "sender_id"]:
        required_text(request.get(field), field, 256)
    target_time = datetime.fromisoformat(checked_timestamp(request.get("sent_at")))
    limit = request.get("context_message_limit")
    budget = request.get("context_text_character_budget")
    if type(limit) is not int or limit < 20 or limit > 25:
        raise ValueError("Context message limit must be 20 to 25.")
    if type(budget) is not int or budget < 0 or budget > 24000 or request.get("context_age_limit") is not None:
        raise ValueError("Invalid context budget or age cutoff.")
    recent = request.get("recent_messages")
    if not isinstance(recent, list) or len(recent) > limit:
        raise ValueError("Invalid preceding-message window.")
    messages: list[dict] = []
    seen: set[str] = set()
    text_size = 0
    previous = None
    for message in recent:
        if not isinstance(message, dict):
            raise ValueError("Invalid context message.")
        message_id = required_text(message.get("message_id"), "message ID", 256)
        if message_id == request["source_message_id"] or message_id in seen:
            raise ValueError("Repeated or target message inside preceding window.")
        seen.add(message_id)
        sent_at = checked_timestamp(message.get("sent_at"))
        current = datetime.fromisoformat(sent_at)
        if current > target_time or (previous is not None and current < previous):
            raise ValueError("Context must be preceding and chronological.")
        previous = current
        text = optional_text(message.get("text"), 4000)
        if text is not None:
            text_size += len(text)
        for flag in ["text_truncated", "media_not_interpreted"]:
            if type(message.get(flag)) is not bool:
                raise ValueError("Context flags must be booleans.")
        if message.get("kind") not in ["text", "sticker", "image", "audio", "other"]:
            raise ValueError("Invalid context kind.")
        messages.append({
            "message_id": message_id,
            "sender_id": required_text(message.get("sender_id"), "sender", 256),
            "sent_at": sent_at, "text": text, "text_truncated": message["text_truncated"],
            "kind": message["kind"], "media_not_interpreted": message["media_not_interpreted"],
            "reply_to_message_id": optional_text(message.get("reply_to_message_id"), 256),
        })
    if text_size > budget or type(request.get("target_text_truncated")) is not bool:
        raise ValueError("Text budget or target truncation flag is invalid.")
    user = request.get("user_context")
    if not isinstance(user, dict) or not isinstance(user.get("preferences"), dict):
        raise ValueError("Missing recipient presentation settings.")
    preferences = user["preferences"]
    # Projection is intentional: no recipient routing, feedback or older history.
    return {
        "schema_version": 2, "policy_version": request["policy_version"],
        "source_message_id": request["source_message_id"], "platform": request["platform"],
        "conversation_id": request["conversation_id"], "sender_id": request["sender_id"],
        "sent_at": request["sent_at"], "target_text": optional_text(request.get("target_text"), 4000),
        "target_text_truncated": request["target_text_truncated"],
        "reply_to_message_id": optional_text(request.get("reply_to_message_id"), 256),
        "recent_messages": messages, "context_message_limit": limit,
        "context_text_character_budget": budget, "context_age_limit": None,
        "user_context": {
            "preferences": {
                "language": required_text(preferences.get("language"), "language", 64),
                "explanation_length": required_text(preferences.get("explanation_length"), "length", 32),
            },
            "preferences_source": required_text(user.get("preferences_source"), "preferences source", 64),
            "relationship": optional_text(user.get("relationship"), 128),
            "relationship_source": optional_text(user.get("relationship_source"), 64),
        },
    }


def apply_candidate_policy(source_id: str, output: dict) -> dict:
    required_text(source_id, "source ID", 256)
    fields = ["candidates", "candidate_relation", "rankable", "context_cue", "uncertainty_caveat"]
    if not isinstance(output, dict) or set(output.keys()) != set(fields):
        raise ValueError("Invalid candidate output fields.")
    candidates = output["candidates"]
    relation = output["candidate_relation"]
    rankable = output["rankable"]
    if not isinstance(candidates, list) or type(rankable) is not bool or not isinstance(relation, str):
        raise ValueError("Invalid candidate types.")
    counts = {"none": 0, "single": 1, "compatible": 2, "opposing": 2}
    if relation not in counts or len(candidates) != counts[relation]:
        raise ValueError("Candidate count does not match relation.")
    normalized: list[str] = []
    for candidate in candidates:
        text = required_text(candidate, "candidate", 1000)
        normalized.append(" ".join(text.split()).casefold())
    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate candidates.")
    for field in ["context_cue", "uncertainty_caveat"]:
        if not isinstance(output[field], str) or len(output[field]) > 1000:
            raise ValueError("Invalid cue or uncertainty caveat.")
    if relation == "none" and rankable:
        raise ValueError("No candidates cannot be rankable.")
    if candidates and not output["uncertainty_caveat"].strip():
        raise ValueError("An interpretation requires an uncertainty caveat.")
    result = {
        "source_message_id": source_id, "status": "unsupported", "meaning": "",
        "alternative": None, "context_cue": output["context_cue"],
        "uncertainty_caveat": output["uncertainty_caveat"], "candidate_relation": relation,
    }
    if not candidates or not rankable:
        return result
    result["meaning"] = candidates[0]
    result["status"] = "interpreted" if relation == "single" else "ambiguous"
    if relation == "compatible":
        result["alternative"] = candidates[1]
    return result


def interpret_sticker(request: dict, adapter: Any) -> dict:
    snapshot = deepcopy(request)
    adapter.start_run(snapshot)
    try:
        context = model_context(snapshot)
        output = adapter.generate(snapshot, context)
        if not isinstance(output, dict):
            raise ValueError("Candidate response must be an object.")
        result = apply_candidate_policy(snapshot["source_message_id"], output)
        adapter.finish_run(result)
        return result
    except Exception as exc:
        # Keep the snapshot and failure separately; never fabricate a meaning.
        adapter.fail_run(type(exc).__name__)
        raise
