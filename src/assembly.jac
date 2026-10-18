"""Pure policy at the T2/T3/T4 assembly boundaries."""
import from .interpreter { interpret_sticker }
import from .routing { verified_direct }

def interpret_saved(request: dict, vision: any) -> dict {
    return interpret_sticker(request, vision);
}

def check_route(delivery: dict, expected: dict, current: dict) {
    for key in ["platform", "conversation_id", "recipient_id", "destination", "members", "source_kind", "source_verified", "assistant_id"] {
        if expected.get(key) != current.get(key) { raise PermissionError("Enrollment changed before send"); }
    }
    if current.get("enabled") is not True or delivery.get("recipient_id") != current.get("recipient_id")
        or delivery.get("source_conversation_id") != current.get("conversation_id") {
        raise PermissionError("Private delivery is not enrolled");
    }
    if current.get("source_sender_id") not in current["members"] {
        raise PermissionError("Source membership revoked");
    }
    if current["destination"] == current["conversation_id"] and not verified_direct(current) {
        raise PermissionError("Direct-source verification revoked");
    }
}

def receipt_policy(receipt: dict) -> dict {
    # A lost response may follow a successful send. Only definite failures permit retry.
    if receipt.get("status") == "accepted" and receipt.get("provider_message_id") {
        return {"status": "accepted", "provider_message_id": receipt["provider_message_id"],
            "provider_idempotency_key": receipt["idempotency_key"]};
    }
    definite = ["invalid_delivery", "unauthorized_destination", "destination_binding_mismatch",
        "destination_not_private", "provider_http_400", "provider_http_401", "provider_http_403",
        "provider_http_404", "provider_http_409", "provider_http_413", "provider_http_415",
        "provider_http_422", "provider_http_429"];
    return {"status": "rejected" if receipt.get("error_code") in definite else "unknown"};
}
