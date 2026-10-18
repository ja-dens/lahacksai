"""T5 coordinator over injected T2/T3/T4 ports; no live client is constructed."""

from __future__ import annotations
from typing import Any
import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path
from .routing import verified_direct


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def request_digest(request: dict) -> str:
    encoded = json.dumps(
        request, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def timestamp(value: str) -> Any:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed


def load_settings(environ: dict | None = None) -> dict:
    # Explicit overrides only; never load .env or construct live clients here.
    settings = dict(
        json.loads(
            (
                Path(str(__file__)).resolve().parents[1] / "config" / "defaults.v2.json"
            ).read_text()
        )
    )
    if environ is not None:
        if "CONTEXT_MESSAGE_LIMIT" in environ:
            settings["context_message_limit"] = int(environ["CONTEXT_MESSAGE_LIMIT"])
        if "EXPLANATION_LANGUAGE" in environ:
            settings["language"] = environ["EXPLANATION_LANGUAGE"]
    validate_settings(settings)
    return settings


def validate_settings(settings: dict) -> None:
    limit = settings.get("context_message_limit")
    if type(limit) is not int or limit < 20 or limit > 25:
        raise ValueError("CONTEXT_MESSAGE_LIMIT must be 20–25")
    if (
        settings.get("contract_version") != 2
        or settings.get("context_age_limit") is not None
    ):
        raise ValueError("Expected v2 context without age cutoff")
    if settings.get("feedback_live_retrieval_enabled") is not False:
        raise ValueError("Live feedback retrieval is disabled")
    if (
        not isinstance(settings.get("language"), str)
        or not settings["language"].strip()
    ):
        raise ValueError("Explanation language is required")
    for key in [
        "context_text_character_budget",
        "message_text_character_limit",
        "target_text_character_limit",
        "target_sticker_max_bytes",
    ]:
        if type(settings.get(key)) is not int or settings[key] < 1:
            raise ValueError("Invalid content limit: " + key)


def create_pipeline(
    store: Any, interpreter: Any, transport: Any, settings: dict | None = None
) -> dict:
    configured = load_settings() if settings is None else dict(clone(settings))
    validate_settings(configured)
    return {
        "store": store,
        "interpreter": interpreter,
        "transport": transport,
        "settings": configured,
    }


def validate_request(job: dict, settings: dict) -> dict:
    request = dict(job["request"])
    if request_digest(request) != job["request_sha256"]:
        raise ValueError("Saved snapshot hash mismatch")
    fields = {
        "schema_version",
        "policy_version",
        "source_message_id",
        "platform",
        "conversation_id",
        "sender_id",
        "recipient_id",
        "sent_at",
        "target_text",
        "target_text_truncated",
        "reply_to_message_id",
        "sticker",
        "recent_messages",
        "context_message_limit",
        "context_text_character_budget",
        "context_age_limit",
        "user_context",
    }
    if set(request) - {"interpreter"} != fields or request["schema_version"] != 2:
        raise ValueError("Unexpected request fields")
    if (
        request["context_message_limit"] != settings["context_message_limit"]
        or request["context_age_limit"] is not None
    ):
        raise ValueError("Context policy mismatch")
    if (
        request["context_text_character_budget"]
        != settings["context_text_character_budget"]
    ):
        raise ValueError("Context budget mismatch")
    messages = request["recent_messages"]
    if (
        not isinstance(messages, list)
        or len(messages) > settings["context_message_limit"]
    ):
        raise ValueError("Context message limit exceeded")
    target_time = timestamp(str(request["sent_at"]))
    previous = None
    text_size = 0
    for message in messages:
        when = timestamp(str(message["sent_at"]))
        if when > target_time or (previous is not None and when < previous):
            raise ValueError("Context contains future or unordered messages")
        if message["message_id"] == request["source_message_id"]:
            raise ValueError("Target cannot also be a preceding message")
        text = message.get("text")
        if text is not None:
            if (
                not isinstance(text, str)
                or len(text) > settings["message_text_character_limit"]
            ):
                raise ValueError("Preceding text exceeds limit")
            text_size += len(text)
        previous = when
    if text_size > settings["context_text_character_budget"]:
        raise ValueError("Recent text exceeds budget")
    target_text = request["target_text"]
    if target_text is not None and (
        not isinstance(target_text, str)
        or len(target_text) > settings["target_text_character_limit"]
    ):
        raise ValueError("Target text exceeds limit")
    context = request["user_context"]
    if set(context) != {
        "preferences",
        "preferences_source",
        "relationship",
        "relationship_source",
    }:
        raise ValueError("Unexpected user context; feedback is evaluation-only")
    if set(context["preferences"]) != {"language", "explanation_length"}:
        raise ValueError("Unexpected presentation settings")
    return dict(clone(request))


def private_route(store: Any, window_id: int, request: dict) -> dict:
    # Resolve trusted enrollment again immediately before sending.
    route = dict(store.resolve_route(window_id))
    if route.get("enabled") is not True:
        raise PermissionError("Recipient paused or unenrolled")
    for key in ["platform", "conversation_id", "recipient_id"]:
        if route.get(key) != request[key]:
            raise PermissionError("Enrollment identity mismatch")
    if (
        request["sender_id"] not in route["members"]
        or request["recipient_id"] not in route["members"]
    ):
        raise PermissionError("Conversation membership missing")
    destination = route.get("destination")
    if (
        not isinstance(destination, str)
        or not destination.strip()
        or (destination == request["conversation_id"] and (not verified_direct(route)))
    ):
        raise PermissionError("Verified private destination required")
    return route


def supported_media(request: dict, settings: dict) -> bool:
    media = request.get("sticker")
    if (
        not isinstance(media, dict)
        or media.get("mime_type") not in settings["target_sticker_mime_types"]
    ):
        return False
    try:
        data = base64.b64decode(str(media["data_base64"]), validate=True)
        mime_type = media.get("mime_type")
        signature_matches = (
            (mime_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
            or (mime_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))
            or (mime_type == "image/webp" and len(data) >= 12
                and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
        )
        return (
            len(data) <= settings["target_sticker_max_bytes"]
            and signature_matches
            and (hashlib.sha256(data).hexdigest() == media.get("sha256"))
        )
    except (ValueError, TypeError, KeyError):
        return False


def validate_result(result: Any, source_id: str) -> dict:
    fields = {
        "source_message_id",
        "status",
        "meaning",
        "context_cue",
        "alternative",
        "uncertainty_caveat",
        "candidate_relation",
    }
    if (
        not isinstance(result, dict)
        or set(result) != fields
        or result.get("source_message_id") != source_id
    ):
        raise ValueError("Interpreter result violates v2 boundary")
    for key in ["meaning", "context_cue", "uncertainty_caveat"]:
        if not isinstance(result[key], str):
            raise ValueError("Invalid result text")
    alternative = result["alternative"]
    if alternative is not None and (
        not isinstance(alternative, str) or not alternative.strip()
    ):
        raise ValueError("Invalid alternative")
    status = result["status"]
    relation = result["candidate_relation"]
    if status not in ["interpreted", "ambiguous", "unsupported"] or relation not in [
        "none",
        "single",
        "compatible",
        "opposing",
    ]:
        raise ValueError("Invalid interpretation state")
    if alternative is not None and (relation != "compatible" or status != "ambiguous"):
        raise ValueError("Only compatible meanings can be shown together")
    if status == "unsupported" and alternative is not None:
        raise ValueError("Unsupported pair")
    if status != "unsupported" and (not result["meaning"].strip()):
        raise ValueError("Missing meaning")
    if status == "interpreted" and relation != "single":
        raise ValueError("Interpreted result requires one meaning")
    if status == "ambiguous" and relation not in ["compatible", "opposing"]:
        raise ValueError("Ambiguous result requires candidate relation")
    if status == "ambiguous" and relation == "compatible" and (alternative is None):
        raise ValueError("Compatible pair requires an alternative")
    if (
        alternative is not None
        and alternative.strip().casefold() == result["meaning"].strip().casefold()
    ):
        raise ValueError("Duplicate meanings are not two interpretations")
    if (
        relation in ["compatible", "opposing"]
        and status != "unsupported"
        and (not result["uncertainty_caveat"].strip())
    ):
        raise ValueError("Ambiguous meanings require a caveat")
    return dict(clone(result))


def unsupported_result(source_id: str) -> dict:
    return {
        "source_message_id": source_id,
        "status": "unsupported",
        "meaning": "",
        "context_cue": "Unsupported sticker media",
        "alternative": None,
        "uncertainty_caveat": "",
        "candidate_relation": "none",
    }


def format_delivery(request: dict, result: dict) -> dict:
    parts = [result["meaning"]]
    if result["alternative"] is not None:
        parts.append(result["alternative"])
    if result["uncertainty_caveat"]:
        parts.append(result["uncertainty_caveat"])
    if result["status"] == "unsupported":
        parts = [
            "I cannot reliably interpret this sticker from the available information."
        ]
    return {
        "recipient_id": request["recipient_id"],
        "source_conversation_id": request["conversation_id"],
        "source_message_id": request["source_message_id"],
        "text": "\n".join(parts),
    }


def outcome(window_id: int, status: str) -> dict:
    return {
        "window_id": window_id,
        "status": status,
        "delivered": False,
        "phone_delivery_verified": False,
    }


def run_window(pipeline: dict, window_id: int, retry: bool = False) -> dict:
    store = pipeline["store"]
    job = dict(store.load_job(window_id))
    if job.get("window_id") != window_id:
        store.mark_failure(window_id, "blocked", "WindowIdentityMismatch")
        return outcome(window_id, "blocked")
    state = job["state"]
    if state not in [
        "pending",
        "interpreted",
        "accepted",
        "interpreting",
        "sending",
        "delivery_unknown",
        "interpretation_failed",
        "send_failed",
        "blocked",
    ]:
        store.mark_failure(window_id, "blocked", "UnknownJobState")
        return outcome(window_id, "blocked")
    if state == "accepted":
        return outcome(window_id, "already_accepted")
    if state in ["sending", "delivery_unknown", "interpreting"]:
        return outcome(window_id, "reconciliation_required")
    if state in ["interpretation_failed", "send_failed", "blocked"] and (not retry):
        return outcome(window_id, "retry_required")
    try:
        request = validate_request(job, dict(pipeline["settings"]))
        private_route(store, window_id, request)
    except Exception as error:
        store.mark_failure(window_id, "blocked", type(error).__name__)
        return outcome(window_id, "blocked")
    result = job.get("result")
    if result is None:
        # Persist a claim before inference. Interrupted calls need reconciliation,
        # rather than silently repeating a possible billed request.
        if not store.claim(window_id, "interpreting"):
            return outcome(window_id, "busy")
        try:
            raw = (
                pipeline["interpreter"](clone(request))
                if supported_media(request, dict(pipeline["settings"]))
                else unsupported_result(str(request["source_message_id"]))
            )
            result = validate_result(raw, str(request["source_message_id"]))
            store.save_result(window_id, result)
        except Exception as error:
            store.mark_failure(window_id, "interpretation_failed", type(error).__name__)
            return outcome(window_id, "interpretation_failed")
    try:
        result = validate_result(result, str(request["source_message_id"]))
        route = private_route(store, window_id, request)
        delivery = format_delivery(request, result)
    except Exception as error:
        store.mark_failure(window_id, "blocked", type(error).__name__)
        return outcome(window_id, "blocked")
    if not store.claim(window_id, "sending"):
        return outcome(window_id, "busy")
    try:
        # Internal idempotency metadata is not a new v2 wire field.
        receipt = dict(
            pipeline["transport"].send_private(
                delivery, clone(route), str(job["idempotency_key"])
            )
        )
        if receipt.get("status") == "rejected":
            store.mark_failure(window_id, "send_failed", "ProviderRejected")
            return outcome(window_id, "send_failed")
        if (
            receipt.get("status") != "accepted"
            or not isinstance(receipt.get("provider_message_id"), str)
            or (not receipt["provider_message_id"].strip())
        ):
            raise ValueError("No definitive provider acknowledgment")
        saved_receipt = {
            "status": "accepted",
            "provider_message_id": receipt["provider_message_id"],
        }
        if "provider_idempotency_key" in receipt:
            key = receipt["provider_idempotency_key"]
            if not isinstance(key, str) or not key.strip() or len(key) > 256:
                raise ValueError("Invalid provider send key")
            saved_receipt["provider_idempotency_key"] = key
        store.mark_accepted(window_id, saved_receipt)
    except Exception as error:
        store.mark_failure(window_id, "delivery_unknown", type(error).__name__)
        return outcome(window_id, "reconciliation_required")
    return outcome(window_id, "accepted")


def process_event(
    pipeline: dict, event: dict, authenticated: bool = False
) -> list[dict]:
    # Authentication is an out-of-band verifier result, never a payload flag.
    if authenticated is not True:
        return [{"status": "rejected_unauthenticated", "delivered": False}]
    if event.get("from_assistant") is True:
        return [{"status": "ignored_assistant", "delivered": False}]
    settings = dict(clone(pipeline["settings"]))
    if hasattr(pipeline["interpreter"], "metadata"):
        metadata = dict(pipeline["interpreter"].metadata)
        settings["interpreter_metadata"] = {
            key: metadata[key]
            for key in ["provider", "model", "prompt_sha256", "prompt_version"]
            if key in metadata
        }
    ids = pipeline["store"].observe(clone(event), settings)
    if event["kind"] != "sticker":
        return [{"status": "history_only", "delivered": False}]
    if not ids:
        return [{"status": "ignored_unenrolled_or_paused", "delivered": False}]
    return [run_window(pipeline, int(window_id)) for window_id in ids]
