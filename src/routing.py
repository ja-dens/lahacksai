"""Direct-source permission comes only from trusted enrollment, never the event."""

from __future__ import annotations


def verified_direct(route: dict) -> bool:
    members = route.get("members")
    assistant = route.get("assistant_id")
    recipient = route.get("recipient_id")
    return (
        route.get("source_kind") == "direct"
        and route.get("source_verified") is True
        and isinstance(members, list)
        and (len(members) == 2)
        and isinstance(assistant, str)
        and bool(assistant.strip())
        and (assistant != recipient)
        and (set(members) == {assistant, recipient})
    )
