"""Validate frozen evidence and enforce the product's candidate policy."""

from __future__ import annotations
from typing import Any
import base64
import binascii
import hashlib
import unicodedata
from datetime import datetime


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def text_value(
    value: Any, label: str, maximum: int, nullable: bool = False
) -> str | None:
    if value is None and nullable:
        return None
    require(isinstance(value, str), label + " must be text")
    require(len(str(value)) <= maximum, label + " exceeds its character limit")
    return str(value)


def identity(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), label + " is required")
    return str(value)


def timestamp(value: Any) -> datetime:
    require(isinstance(value, str), "Timestamp must be text")
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "Timestamp needs a timezone")
    return parsed


def boolean(value: Any, label: str) -> bool:
    require(isinstance(value, bool), label + " must be boolean")
    return bool(value)


def integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    require(
        isinstance(value, int) and (not isinstance(value, bool)),
        label + " must be an integer",
    )
    parsed = int(value)
    require(minimum <= parsed <= maximum, label + " is outside its allowed range")
    return parsed


def prepare_media(media: Any) -> dict:
    require(isinstance(media, dict), "Sticker media is required")
    require(
        media.get("mime_type") == "image/png",
        "Only static PNG stickers are supported initially",
    )
    encoded = media.get("data_base64")
    require(
        isinstance(encoded, str) and 0 < len(encoded) <= 6666668,
        "Invalid encoded sticker size",
    )
    encoded = str(encoded)
    try:
        data = base64.b64decode(str(encoded), validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("Sticker base64 is invalid")
    require(0 < len(data) <= 5000000, "Sticker must contain at most 5 MB")
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), "Sticker is not a PNG")
    digest = hashlib.sha256(data).hexdigest()
    require(media.get("sha256") == digest, "Sticker digest does not match its bytes")
    return {"mime_type": "image/png", "data_base64": encoded, "sha256": digest}


def prepare_user_context(value: Any) -> dict:
    require(isinstance(value, dict), "User context is required")
    require(
        set(
            ["preferences", "preferences_source", "relationship", "relationship_source"]
        ).issubset(set(value.keys())),
        "User-context fields are missing",
    )
    preferences = value.get("preferences")
    require(isinstance(preferences, dict), "Presentation preferences are required")
    language = str(text_value(preferences.get("language"), "Language", 64))
    require(bool(language.strip()), "Language is required")
    length = preferences.get("explanation_length")
    require(length in ["short", "detailed"], "Unsupported explanation length")
    relationship = text_value(value.get("relationship"), "Relationship", 256, True)
    if relationship is not None:
        require(bool(relationship.strip()), "Relationship cannot be empty")
    preferences_source = text_value(
        value.get("preferences_source"), "Preference source", 128
    )
    relationship_source = text_value(
        value.get("relationship_source"), "Relationship source", 128, True
    )
    return {
        "preferences": {"language": language, "explanation_length": length},
        "preferences_source": preferences_source,
        "relationship": relationship,
        "relationship_source": relationship_source,
    }


def prepare_request(request: Any) -> dict:
    require(isinstance(request, dict), "Interpretation request must be an object")
    request = dict(request)
    request_fields: list[str] = [
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
    ]
    require(
        set(request_fields).issubset(set(request.keys())),
        "Normalized request fields are missing",
    )
    integer(request.get("schema_version"), "Schema version", 2, 2)
    source = identity(request.get("source_message_id"), "Source message ID")
    for field in [
        "platform",
        "conversation_id",
        "sender_id",
        "recipient_id",
        "policy_version",
    ]:
        identity(request.get(field), field)
    target_time = timestamp(request.get("sent_at"))
    limit = integer(request.get("context_message_limit"), "Context count", 20, 25)
    budget = integer(
        request.get("context_text_character_budget"), "Context text budget", 1, 24000
    )
    require(
        request.get("context_age_limit", "missing") is None,
        "Context must have no age cutoff",
    )
    target_text = text_value(request.get("target_text"), "Target text", 4000, True)
    target_truncated = boolean(
        request.get("target_text_truncated"), "Target truncation flag"
    )
    reply = text_value(
        request.get("reply_to_message_id"), "Target reply reference", 1000, True
    )
    messages = request.get("recent_messages")
    require(
        isinstance(messages, list) and len(messages) <= limit,
        "Recent messages exceed the frozen window",
    )
    recent = []
    seen = set()
    previous_time: datetime | None = None
    characters = 0
    for message in messages:
        require(isinstance(message, dict), "Recent message must be an object")
        message_fields: list[str] = [
            "message_id",
            "sender_id",
            "sent_at",
            "text",
            "text_truncated",
            "kind",
            "media_not_interpreted",
            "reply_to_message_id",
        ]
        require(
            set(message_fields).issubset(set(message.keys())),
            "Normalized prior-message fields are missing",
        )
        message_id = identity(message.get("message_id"), "Prior message ID")
        require(
            message_id != source and message_id not in seen,
            "Prior message identities must be distinct from the target",
        )
        seen.add(message_id)
        sent = timestamp(message.get("sent_at"))
        require(sent <= target_time, "Future messages are not valid context")
        if previous_time is not None:
            require(previous_time <= sent, "Recent context must be chronological")
        previous_time = sent
        body = text_value(message.get("text"), "Prior text", 4000, True)
        if body is not None:
            characters += len(str(body))
        kind = message.get("kind")
        require(
            kind in ["text", "sticker", "image", "audio", "other"],
            "Unknown prior content kind",
        )
        media_flag = boolean(message.get("media_not_interpreted"), "Prior-media flag")
        require(
            media_flag == (kind != "text"),
            "Prior media must be explicitly marked uninterpreted",
        )
        recent.append(
            {
                "message_id": message_id,
                "sender_id": identity(message.get("sender_id"), "Prior sender ID"),
                "sent_at": message["sent_at"],
                "text": body,
                "text_truncated": boolean(
                    message.get("text_truncated"), "Prior truncation flag"
                ),
                "kind": kind,
                "media_not_interpreted": media_flag,
                "reply_to_message_id": text_value(
                    message.get("reply_to_message_id"),
                    "Prior reply reference",
                    1000,
                    True,
                ),
            }
        )
    require(characters <= budget, "Recent text exceeds the frozen character budget")
    media = prepare_media(request.get("sticker"))
    # Project model evidence explicitly: routing, feedback and archives stay outside.
    return {
        "schema_version": 2,
        "policy_version": request["policy_version"],
        "source_message_id": source,
        "sender_id": request["sender_id"],
        "sent_at": request["sent_at"],
        "target_text": target_text,
        "target_text_truncated": target_truncated,
        "reply_to_message_id": reply,
        "recent_messages": recent,
        "context_message_limit": limit,
        "context_text_character_budget": budget,
        "context_age_limit": None,
        "user_context": prepare_user_context(request.get("user_context")),
        "sticker": media,
    }


def model_output_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "candidates": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 2000},
                "maxItems": 2,
            },
            "candidate_relation": {
                "type": "string",
                "enum": ["none", "single", "compatible", "opposing"],
            },
            "rankable": {"type": "boolean"},
            "context_cue": {"type": "string", "maxLength": 1000},
            "uncertainty_caveat": {"type": "string", "maxLength": 1000},
        },
        "required": [
            "candidates",
            "candidate_relation",
            "rankable",
            "context_cue",
            "uncertainty_caveat",
        ],
    }


def validate_model_output(raw: Any) -> dict:
    require(isinstance(raw, dict), "Model output must be an object")
    required = set(model_output_schema()["required"])
    require(set(raw.keys()) == required, "Model output fields do not match the schema")
    candidates = raw["candidates"]
    require(
        isinstance(candidates, list) and len(candidates) <= 2,
        "Expected at most two ranked candidates",
    )
    relation = raw["candidate_relation"]
    require(
        relation in ["none", "single", "compatible", "opposing"],
        "Invalid candidate relation",
    )
    rankable = boolean(raw["rankable"], "Rankability")
    cue = str(text_value(raw["context_cue"], "Context cue", 1000)).strip()
    caveat = str(
        text_value(raw["uncertainty_caveat"], "Uncertainty caveat", 1000)
    ).strip()
    cleaned = []
    distinct = set()
    for candidate in candidates:
        meaning = str(text_value(candidate, "Candidate", 2000)).strip()
        require(bool(meaning), "Candidate cannot be empty")
        normalized = " ".join(unicodedata.normalize("NFKC", meaning).split()).casefold()
        require(normalized not in distinct, "Duplicate candidates are invalid")
        distinct.add(normalized)
        cleaned.append(meaning)
    if relation == "none":
        require(
            len(cleaned) == 0 and (not rankable),
            "No meaning requires zero candidates and rankable=false",
        )
    elif relation == "single":
        require(
            len(cleaned) == 1 and rankable,
            "A single meaning requires one rankable candidate",
        )
    else:
        require(len(cleaned) == 2, "A pair requires exactly two meanings")
        require(bool(caveat), "A pair requires an explicit uncertainty caveat")
    return {
        "candidates": cleaned,
        "candidate_relation": relation,
        "rankable": rankable,
        "context_cue": cue,
        "uncertainty_caveat": caveat,
    }


def apply_policy(raw: Any, source_message_id: str) -> dict:
    source = identity(source_message_id, "Source message ID")
    output = validate_model_output(raw)
    candidates = list(output["candidates"])
    relation = output["candidate_relation"]
    unsupported = relation == "none" or (
        relation == "opposing" and (not output["rankable"])
    )
    return {
        "source_message_id": source,
        "status": (
            "unsupported"
            if unsupported
            else "ambiguous" if len(candidates) == 2 else "interpreted"
        ),
        "meaning": "" if unsupported else candidates[0],
        "alternative": candidates[1] if relation == "compatible" else None,
        "context_cue": output["context_cue"],
        "uncertainty_caveat": output["uncertainty_caveat"],
        "candidate_relation": relation,
    }


def interpret_sticker(request: dict, vision: Any) -> dict:
    # Preserve the caller's snapshot; operational failures must not invent meanings.
    prepare_request(request)
    return apply_policy(vision(request), str(request["source_message_id"]))
