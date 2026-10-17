"""Check published demo interfaces without importing application/vendor code."""

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "contracts"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    event = load("incoming_message")
    request = load("interpretation_request")
    require(event["platform"] == "demo", "Only synthetic demo data belongs here")
    require(event["message_id"] == request["source_message_id"] == "demo-3", "Source identity mismatch")
    require(event["conversation_id"] == request["conversation_id"], "Conversation mismatch")
    require(event["kind"] == "sticker" and not event["from_assistant"], "Expected incoming sticker")
    require(request["schema_version"] == 2, "Expected v2 request")
    require(20 <= request["context_message_limit"] <= 25, "Wrong context limit")
    require(request["context_age_limit"] is None, "Age cutoff is not selected")
    require(len(request["recent_messages"]) <= request["context_message_limit"], "Context window overflow")
    target_time = datetime.fromisoformat(request["sent_at"])
    times = [datetime.fromisoformat(m["sent_at"]) for m in request["recent_messages"]]
    require(times == sorted(times) and all(t <= target_time for t in times), "Context ordering mismatch")
    require(all(m["message_id"] != event["message_id"] for m in request["recent_messages"]), "Target duplicated in prior context")
    require(set(request["user_context"]) == {"preferences", "preferences_source", "relationship", "relationship_source"}, "Unexpected user-context inputs")
    require("destination" not in request and "feedback" not in request, "Routing or feedback leaked into model input")
    media = request["sticker"]
    png = base64.b64decode(media["data_base64"], validate=True)
    require(png == (ROOT / "fixtures/stickers/hamster_tongue_out.png").read_bytes(), "Image fixture mismatch")
    require(png.startswith(b"\x89PNG\r\n\x1a\n") and len(png) <= 5_000_000, "Invalid initial image format/size")
    require(hashlib.sha256(png).hexdigest() == media["sha256"], "Image digest mismatch")
    require(event["sticker"] == media, "Event and request images differ")
    saved = load("saved_exchange")
    require(saved["synthetic"] is True and saved["request"] == request, "Saved-window mismatch")
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    require(hashlib.sha256(canonical.encode()).hexdigest() == saved["request_sha256"], "Request digest mismatch")
    require(saved["interpretation_source"] == "fixed_fixture" and saved["delivered"] is False, "Fixture labeled as live")
    for suffix, candidate_name, result_name in [
        ("single", "candidate_single", "interpretation_result"),
        ("compatible", "candidate_compatible", "result_compatible"),
        ("opposing", "candidate_opposing", "result_opposing"),
        ("unsupported", "candidate_unsupported", "result_unsupported"),
    ]:
        candidate, result = load(candidate_name), load(result_name)
        require(result["source_message_id"] == event["message_id"], f"{suffix}: wrong source")
        if candidate["candidates"]:
            require(result["meaning"] == candidate["candidates"][0], f"{suffix}: wrong first meaning")
        if suffix == "compatible":
            require(result["alternative"] == candidate["candidates"][1], "Compatible second meaning lost")
        if suffix == "opposing":
            require(result["alternative"] is None and bool(result["uncertainty_caveat"]), "Opposing policy mismatch")
        if suffix == "unsupported":
            require(result["status"] == "unsupported", "Unsupported example lacks fallback status")
    require(saved["result"] == load("interpretation_result"), "Saved result mismatch")
    delivery, feedback, fetch = load("private_delivery"), load("feedback"), load("fetch_requests")
    require(delivery["recipient_id"] == feedback["recipient_id"] == saved["recipient_id"] == fetch["trusted_demo_identity"], "Recipient mismatch")
    require(feedback["window_id"] == saved["window_id"] == fetch["lookup"]["window_id"] == fetch["feedback"]["window_id"], "Window mismatch")
    require(feedback["provenance"] == "recipient_judgment", "Feedback wrongly labeled sender confirmation")
    print("Contract fixtures passed: demo image, v2 inputs, immutable snapshot, output cases, private delivery and Fetch examples. No network calls.")


if __name__ == "__main__":
    main()
