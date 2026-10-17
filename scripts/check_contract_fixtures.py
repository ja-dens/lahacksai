"""Verify the shared v2 examples and defaults using Python's standard library."""

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NULLABLE_TEXT = (str, type(None))
CASES = (
    ("single", "candidate_single", "interpretation_result"),
    ("compatible", "candidate_compatible", "result_compatible"),
    ("opposing", "candidate_opposing", "result_opposing"),
    ("unsupported", "candidate_unsupported", "result_unsupported"),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, required, optional=None, label="record"):
    require(type(value) is dict, f"{label}: expected object")
    optional = optional or {}
    require(set(required) <= set(value), f"{label}: missing required fields")
    require(set(value) <= set(required) | set(optional), f"{label}: unknown fields")
    for name, expected in {**required, **optional}.items():
        if name in value:
            allowed = expected if isinstance(expected, tuple) else (expected,)
            require(type(value[name]) in allowed, f"{label}.{name}: wrong type")


def timestamp(value):
    require(type(value) is str, "Timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "Timestamp requires a timezone")
    return parsed


def load_inputs(root=ROOT):
    fixture_dir = root / "fixtures/contracts"
    bundle = {p.stem: json.loads(p.read_text()) for p in fixture_dir.glob("*.json")}
    defaults = json.loads((root / "config/defaults.v2.json").read_text())
    env_text = (root / ".env.example").read_text()
    image = (root / "fixtures/stickers/laughing.png").read_bytes()
    chat = json.loads((root / "fixtures/chats/joke.json").read_text())
    return bundle, defaults, env_text, image, chat


def validate_defaults(defaults, env_text):
    require(defaults["contract_version"] == 2, "Expected v2 defaults")
    require(type(defaults["context_message_limit"]) is int, "Context default must be an integer")
    require((defaults["context_message_limit_min"], defaults["context_message_limit"], defaults["context_message_limit_max"]) == (20, 25, 25), "Context defaults drifted from the agreed baseline")
    require(defaults["context_age_limit"] is None, "Age cutoff is not selected")
    require(defaults["feedback_live_retrieval_enabled"] is False, "Feedback must remain evaluation-only")
    settings = {}
    for line in env_text.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            require(key not in settings, "Duplicate example setting")
            settings[key] = value
    require(settings["CONTEXT_MESSAGE_LIMIT"] == str(defaults["context_message_limit"]), "Example environment context limit differs from v2 defaults")
    require(settings["EXPLANATION_LANGUAGE"] == defaults["language"], "Example language differs from defaults")
    require(all(not value for key, value in settings.items() if key.endswith("_KEY") or key == "VISION_MODEL"), "Keep credential/model placeholders empty")


def validate_bundle(bundle, defaults, env_text, image, chat):
    validate_defaults(defaults, env_text)
    event, request = bundle["incoming_message"], bundle["interpretation_request"]
    fields(event, {"platform": str, "conversation_id": str, "message_id": str, "sender_id": str,
        "sent_at": str, "from_assistant": bool, "text": NULLABLE_TEXT, "kind": str,
        "sticker": (dict, type(None)), "reply_to_message_id": NULLABLE_TEXT}, label="IncomingMessage")
    fields(request, {"schema_version": int, "policy_version": str, "source_message_id": str,
        "platform": str, "conversation_id": str, "sender_id": str, "recipient_id": str,
        "sent_at": str, "target_text": NULLABLE_TEXT, "target_text_truncated": bool,
        "reply_to_message_id": NULLABLE_TEXT, "sticker": dict, "recent_messages": list,
        "context_message_limit": int, "context_text_character_budget": int,
        "context_age_limit": type(None), "user_context": dict}, {"interpreter": dict}, "InterpretationRequest")
    for key in ("platform", "conversation_id", "sender_id", "sent_at"):
        require(event[key] == request[key], f"Source {key} mismatch")
    require(event["platform"] == "demo", "Only synthetic demo data belongs here")
    require(event["message_id"] == request["source_message_id"] == "demo-3", "Source identity mismatch")
    require(event["kind"] == "sticker" and not event["from_assistant"], "Expected incoming sticker")
    require(request["schema_version"] == 2, "Expected v2 request")
    require(defaults["context_message_limit_min"] <= request["context_message_limit"] <= defaults["context_message_limit_max"], "Wrong context limit")
    require(request["context_text_character_budget"] == defaults["context_text_character_budget"], "Text-budget baseline mismatch")
    require(len(request["recent_messages"]) <= request["context_message_limit"], "Context window overflow")
    target_time, times, identities = timestamp(request["sent_at"]), [], set()
    for message in request["recent_messages"]:
        fields(message, {"message_id": str, "sender_id": str, "sent_at": str,
            "text": NULLABLE_TEXT, "text_truncated": bool, "kind": str,
            "media_not_interpreted": bool, "reply_to_message_id": NULLABLE_TEXT}, label="RecentMessage")
        times.append(timestamp(message["sent_at"]))
        require(message["message_id"] not in identities and message["message_id"] != event["message_id"], "Repeated/target message in preceding context")
        identities.add(message["message_id"])
        require(len(message["text"] or "") <= defaults["message_text_character_limit"], "Per-message text limit exceeded")
    require(times == sorted(times) and all(t <= target_time for t in times), "Context ordering mismatch or future message")
    require(sum(len(m["text"] or "") for m in request["recent_messages"]) <= request["context_text_character_budget"], "Recent-text budget exceeded")
    require(len(request["target_text"] or "") <= defaults["target_text_character_limit"], "Target-text limit exceeded")
    fields(request["user_context"], {"preferences": dict, "preferences_source": str,
        "relationship": NULLABLE_TEXT, "relationship_source": NULLABLE_TEXT}, label="UserContext")
    preferences = request["user_context"]["preferences"]
    fields(preferences, {"language": str, "explanation_length": str}, label="Preferences")
    require(bool(preferences["language"].strip()) and preferences["explanation_length"] in defaults["explanation_lengths"], "Invalid presentation preference")
    media = request["sticker"]
    fields(media, {"data_base64": str, "mime_type": str, "sha256": str}, label="Media")
    png = base64.b64decode(media["data_base64"], validate=True)
    require(png == image, "Image fixture mismatch")
    require(media["mime_type"] in defaults["target_sticker_mime_types"] and png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) <= defaults["target_sticker_max_bytes"], "Invalid initial image format/size")
    require(hashlib.sha256(png).hexdigest() == media["sha256"], "Image digest mismatch")
    require(event["sticker"] == media, "Event and request images differ")
    saved = bundle["saved_exchange"]
    require(saved["synthetic"] is True and saved["request"] == request, "Saved-window mismatch")
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    require(hashlib.sha256(canonical.encode()).hexdigest() == saved["request_sha256"], "Request digest mismatch")
    require(saved["interpretation_source"] == "fixed_fixture" and saved["delivery_status"] == "pending" and saved["delivered"] is False, "Fixture labeled as live/sent")
    for suffix, candidate_name, result_name in CASES:
        candidate, result = bundle[candidate_name], bundle[result_name]
        fields(candidate, {"candidates": list, "candidate_relation": str, "rankable": bool,
            "context_cue": str, "uncertainty_caveat": str}, label=candidate_name)
        fields(result, {"source_message_id": str, "status": str, "meaning": str,
            "context_cue": str, "alternative": NULLABLE_TEXT, "uncertainty_caveat": str,
            "candidate_relation": str}, label="InterpretationResult")
        candidates = candidate["candidates"]
        require(all(type(c) is str and c.strip() for c in candidates) and len(candidates) <= 2, "Invalid candidate list")
        require(len(set(c.strip().casefold() for c in candidates)) == len(candidates), "Duplicate candidate meanings")
        require(result["source_message_id"] == event["message_id"], f"{suffix}: wrong source")
        require(result["context_cue"] == candidate["context_cue"], f"{suffix}: context cue mismatch")
        if candidates:
            require(result["meaning"] == candidates[0], f"{suffix}: wrong first meaning")
        if suffix == "single":
            require(len(candidates) == 1 and candidate["candidate_relation"] == result["candidate_relation"] == "single" and result["status"] == "interpreted" and result["alternative"] is None, "Single-result mismatch")
        elif suffix == "compatible":
            require(len(candidates) == 2 and candidate["candidate_relation"] == result["candidate_relation"] == "compatible" and result["status"] == "ambiguous" and result["alternative"] == candidates[1], "Compatible second meaning lost")
        elif suffix == "opposing":
            require(len(candidates) == 2 and candidate["candidate_relation"] == result["candidate_relation"] == "opposing" and candidate["rankable"] is True and result["status"] == "ambiguous" and result["alternative"] is None and bool(result["uncertainty_caveat"].strip()), "Opposing policy mismatch")
        else:
            require(not candidates and candidate["candidate_relation"] == result["candidate_relation"] == "none" and not candidate["rankable"] and result["status"] == "unsupported" and result["alternative"] is None and not result["meaning"], "Unsupported-result mismatch")
    require(saved["result"] == bundle["interpretation_result"], "Saved result mismatch")
    delivery, feedback, fetch = bundle["private_delivery"], bundle["feedback"], bundle["fetch_requests"]
    fields(delivery, {"recipient_id": str, "source_conversation_id": str, "source_message_id": str, "text": str}, label="DeliveryRequest")
    fields(feedback, {"window_id": int, "recipient_id": str, "selection": str,
        "provenance": str, "created_at": str}, {"note": NULLABLE_TEXT}, "Feedback")
    require(delivery["recipient_id"] == feedback["recipient_id"] == saved["recipient_id"] == request["recipient_id"] == fetch["trusted_demo_identity"] == chat["enrolled_recipient_id"], "Recipient mismatch")
    require(delivery["source_conversation_id"] == request["conversation_id"] and delivery["source_message_id"] == saved["source_message_id"] == request["source_message_id"], "Delivery source mismatch")
    require(delivery["text"] == saved["result"]["meaning"] + "\n" + saved["result"]["uncertainty_caveat"], "Formatted delivery text mismatch")
    require(feedback["window_id"] == saved["window_id"] == fetch["lookup"]["window_id"] == fetch["feedback"]["window_id"], "Window mismatch")
    require(feedback["selection"] in defaults["feedback_selections"], "Invalid feedback selection")
    require(feedback["selection"] != "second" or bool(saved["result"]["alternative"]), "Second feedback choice was not shown")
    require(feedback["provenance"] == "recipient_judgment", "Feedback wrongly labeled sender confirmation")
    timestamp(feedback["created_at"])
    require(chat["synthetic"] is True and fetch["synthetic"] is True, "Only synthetic chats/tools belong in shared fixtures")
    require(chat["platform"] == request["platform"] and chat["conversation_id"] == request["conversation_id"], "Synthetic chat identity mismatch")
    require(chat["messages"][-1]["message_id"] == request["source_message_id"] and chat["fixture_model_output"] == bundle["candidate_single"], "Synthetic chat/result drift")
    expected = chat["messages"][:-1][-request["context_message_limit"]:]
    require([m["message_id"] for m in expected] == [m["message_id"] for m in request["recent_messages"]], "Context does not match the synthetic source window")
    for original, recent in zip(expected, request["recent_messages"]):
        require(original["sender_id"] == recent["sender_id"] and original.get("text") == recent["text"] and timestamp(original["sent_at"]) == timestamp(recent["sent_at"]), "Source message content mismatch")
    require(bool(chat["private_destination"].strip()) and chat["private_destination"] != chat["conversation_id"], "Private destination must be separate from source chat")


def main():
    validate_bundle(*load_inputs())
    print("Contract fixtures passed: v2 fields, defaults, context bounds, synthetic image, saved snapshot, output cases, trusted routing and feedback. No network calls.")


if __name__ == "__main__":
    main()
