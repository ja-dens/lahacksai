"""Application-owned private routing; no network delivery is implied by queuing."""

from __future__ import annotations
import json
from sqlite3 import Connection
from .contracts import canonical, now


def queue_explanation(
    db: Connection, window: dict, enrollment: dict, result: dict
) -> dict:
    if (
        window["recipient_id"] != enrollment["recipient_id"]
        or not enrollment["enabled"]
    ):
        raise ValueError("Recipient is not actively enrolled")
    if (
        window["conversation_id"] != enrollment["conversation_id"]
        or window["platform"] != enrollment["platform"]
    ):
        raise ValueError("Enrollment does not match the source conversation")
    members = json.loads(str(enrollment["members_json"]))
    if (
        window["recipient_id"] not in members
        or enrollment["destination"] == window["conversation_id"]
    ):
        raise ValueError("Private recipient routing could not be verified")
    parts = [result["meaning"]]
    if result.get("alternative"):
        parts.append(result["alternative"])
    if result["uncertainty_caveat"]:
        parts.append(result["uncertainty_caveat"])
    if result["status"] == "unsupported":
        # Temporary English fallback for the initial English demo.
        parts = [
            "I cannot reliably interpret this sticker from the available information."
        ]
    text = "\n".join(parts)
    with db:
        db.execute(
            """INSERT INTO outbox
            (window_id, recipient_id, destination, text, created_at) VALUES (?, ?, ?, ?, ?)""",
            (
                window["id"],
                enrollment["recipient_id"],
                enrollment["destination"],
                text,
                now(),
            ),
        )
        db.execute(
            """UPDATE interpretation_runs SET status='queued', result_json=?, error_code=NULL
            WHERE window_id=?""",
            (canonical(result), window["id"]),
        )
    return {
        "window_id": window["id"],
        "status": "queued",
        "delivered": False,
        "recipient_id": enrollment["recipient_id"],
        "text": text,
    }
