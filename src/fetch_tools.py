"""Saved-result authorization and feedback policy. No model or Photon calls."""

from __future__ import annotations
from typing import Any
from copy import deepcopy


def scoped_exchange(exchanges: list[dict], window_id: int, recipient: str) -> dict:
    if type(window_id) != int or window_id < 1 or (not recipient):
        raise PermissionError("Saved exchange unavailable.")
    for exchange in exchanges:
        if exchange["window_id"] == window_id and exchange["recipient_id"] == recipient:
            return exchange
    # Unknown and other recipients' windows deliberately have the same response.
    raise PermissionError("Saved exchange unavailable.")


def resolve_window(exchanges: list[dict], source_id: str, recipient: str) -> int:
    matches = []
    for exchange in exchanges:
        if (
            exchange["source_message_id"] == source_id
            and exchange["recipient_id"] == recipient
        ):
            matches.append(exchange["window_id"])
    if len(matches) != 1:
        raise PermissionError("Saved exchange unavailable.")
    return int(matches[0])


def get_explanation(exchanges: list[dict], window_id: int, recipient: str) -> dict:
    exchange = scoped_exchange(exchanges, window_id, recipient)
    result = exchange.get("result")
    if not result:
        raise PermissionError("Saved exchange unavailable.")
    # Project saved output only; never expose the request or whole chat.
    return {
        "ok": True,
        "window_id": window_id,
        "source_message_id": exchange["source_message_id"],
        "status": result["status"],
        "meaning": result["meaning"],
        "alternative": result["alternative"],
        "context_cue": result["context_cue"],
        "uncertainty_caveat": result["uncertainty_caveat"],
        "candidate_relation": result["candidate_relation"],
    }


def save_feedback(
    exchanges: list[dict],
    feedback: list[dict],
    window_id: int,
    recipient: str,
    selection: str,
    note: str | None,
    created_at: str,
) -> dict:
    result = get_explanation(exchanges, window_id, recipient)
    if selection not in ["first", "second", "neither", "not_sure"]:
        raise ValueError("Invalid feedback selection.")
    if selection == "first" and (
        result["status"] == "unsupported" or not result["meaning"]
    ):
        raise ValueError("No first interpretation was shown.")
    if selection == "second" and (not result["alternative"]):
        raise ValueError("No second interpretation was shown.")
    if note is not None and (not isinstance(note, str) or len(note) > 2000):
        raise ValueError("Feedback note must be text of at most 2000 characters.")
    record = {
        "feedback_id": len(feedback) + 1,
        "window_id": window_id,
        "recipient_id": recipient,
        "selection": selection,
        "note": note,
        "provenance": "recipient_judgment",
        "created_at": created_at,
    }
    feedback.append(record)
    return {"ok": True, "feedback": deepcopy(record)}


def execute_tool(
    backend: Any,
    receipts: dict,
    tool: str,
    arguments: dict,
    recipient: str,
    command_id: str,
) -> dict:
    if not recipient:
        raise PermissionError("Saved exchange unavailable.")
    if not isinstance(command_id, str) or not command_id.strip():
        raise ValueError("A stable transport command ID is required.")
    allowed = {
        "get_explanation": ["window_id"],
        "save_feedback": ["window_id", "selection", "note"],
    }
    if tool not in allowed or not isinstance(arguments, dict):
        raise ValueError("Unknown tool or invalid arguments.")
    if "window_id" not in arguments:
        raise ValueError("window_id is required.")
    if type(arguments["window_id"]) != int or arguments["window_id"] < 1:
        raise PermissionError("Saved exchange unavailable.")
    for key in arguments:
        if key not in allowed[tool]:
            raise ValueError("Unexpected tool argument.")
    # Recipient comes from the trusted caller, never the tool arguments.
    key = (recipient, command_id)
    payload = {"tool": tool, "arguments": arguments}
    if key in receipts:
        if receipts[key]["payload"] != payload:
            raise ValueError("Command ID reused for a different operation.")
        return dict(deepcopy(receipts[key]["result"]))
    if tool == "get_explanation":
        result = backend.get_explanation(arguments["window_id"], recipient)
    else:
        if "selection" not in arguments or not isinstance(arguments["selection"], str):
            raise ValueError("selection is required.")
        result = backend.save_feedback(
            arguments["window_id"],
            recipient,
            arguments["selection"],
            arguments.get("note"),
        )
    receipts[key] = deepcopy({"payload": payload, "result": result})
    return dict(result)
