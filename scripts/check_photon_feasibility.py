#!/usr/bin/env python3
"""Validate sanitized Photon feasibility fixtures. No network and no secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "fixtures" / "photon_vendor"
FORBIDDEN = ("pho_sk_", "sk-", "api_key", "secret", "+1341")


def main() -> int:
    operations = json.loads((VENDOR / "operations.json").read_text())
    inbound = json.loads((VENDOR / "inbound_text.json").read_text())
    outbound = json.loads((VENDOR / "outbound_text.json").read_text())
    blob = json.dumps({"operations": operations, "inbound": inbound, "outbound": outbound})
    lowered = blob.lower()
    for token in FORBIDDEN:
        if token.lower() in lowered:
            print(f"fixture contains forbidden token {token}", file=sys.stderr)
            return 1
    if inbound["content"]["type"] != "text" or inbound["space"]["kind"] != "direct":
        print("inbound example is not a direct text event", file=sys.stderr)
        return 1
    if outbound["sentBy"]["kind"] != "agent" or outbound["status"] != "delivered":
        print("outbound example is not a delivered agent text", file=sys.stderr)
        return 1
    print("channel:", operations["channel"])
    for item in operations["operations"]:
        print(f"{item['result']:12} {item['name']}")
    print("config names: PHOTON_API_KEY PHOTON_PROJECT_ID PHOTON_ALLOWED_SENDER PHOTON_AGENT_HANDLE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
