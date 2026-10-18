"""Optional ACP adapter over saved results. Run with --demo or --serve-synthetic."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from src import fetch_tools

ROOT = Path(__file__).resolve().parents[2]


class FakeBackend:
    """In-memory substitute for T4's two authorized operations, synthetic only."""

    def __init__(self, exchanges, clock=None):
        if not exchanges or any(record.get("synthetic") is not True for record in exchanges):
            raise ValueError("The public demo backend accepts synthetic records only.")
        self.exchanges = deepcopy(exchanges)
        self.feedback = []
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def resolve_window(self, source_id, authenticated_recipient_id):
        return fetch_tools.resolve_window(self.exchanges, source_id, authenticated_recipient_id)

    def get_explanation(self, window_id, authenticated_recipient_id):
        return fetch_tools.get_explanation(self.exchanges, window_id, authenticated_recipient_id)

    def save_feedback(self, window_id, authenticated_recipient_id, selection, note=None):
        return fetch_tools.save_feedback(self.exchanges, self.feedback, window_id,
                                         authenticated_recipient_id, selection, note, self.clock())


class FetchTools:
    def __init__(self, backend):
        self.backend = backend
        self.receipts = {}

    def call(self, tool, arguments, *, authenticated_recipient_id, command_id):
        try:
            return fetch_tools.execute_tool(self.backend, self.receipts, tool, arguments,
                                            authenticated_recipient_id, command_id)
        except PermissionError:
            return {"ok": False, "error": "Saved exchange unavailable."}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    def handle_chat(self, text, *, authenticated_recipient_id, command_id):
        """Deliberately bounded demo grammar; no LLM interpretation or identity inference."""
        if not authenticated_recipient_id:
            return {"ok": False, "error": "Saved exchange unavailable."}
        lookup = re.fullmatch(r"Explain the sticker in saved demo exchange ([\w-]+)\.?", text, re.I)
        feedback = re.fullmatch(r"Mark interpretation (one|two) as helpful for ([\w-]+)\.?", text, re.I)
        if len(text) > 2000 or not (lookup or feedback):
            return {"ok": False, "error": "Use: Explain the sticker in saved demo exchange demo-3. "
                    "Or: Mark interpretation one as helpful for demo-3."}
        try:
            source_id = lookup[1] if lookup else feedback[2]
            window_id = self.backend.resolve_window(source_id, authenticated_recipient_id)
        except PermissionError:
            return {"ok": False, "error": "Saved exchange unavailable."}
        arguments = {"window_id": window_id}
        if feedback:
            arguments["selection"] = {"one": "first", "two": "second"}[feedback[1].lower()]
        return self.call("get_explanation" if lookup else "save_feedback", arguments,
                         authenticated_recipient_id=authenticated_recipient_id, command_id=command_id)


def make_protocol(tools, resolve_identity):
    """resolve_identity receives a verified transport sender, not user text."""
    from uagents import Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec,
    )

    protocol = Protocol(spec=chat_protocol_spec)

    @protocol.on_message(ChatMessage)
    async def handle_message(ctx, sender, msg):
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc),
                                                   acknowledged_msg_id=msg.msg_id))
        try:
            result = tools.handle_chat("".join(item.text for item in msg.content if isinstance(item, TextContent)),
                                      authenticated_recipient_id=resolve_identity(sender),
                                      command_id=f"{sender}:{msg.msg_id}")
        except Exception as exc:
            ctx.logger.error(f"Fetch saved-result operation failed ({type(exc).__name__}).")
            result = {"ok": False, "error": "Saved-result service unavailable. Please try again later."}
        await ctx.send(sender, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                       content=[TextContent(type="text", text=json.dumps(result)),
                                EndSessionContent(type="end-session")]))

    @protocol.on_message(ChatAcknowledgement)
    async def handle_ack(ctx, sender, msg):
        pass

    return protocol


def demo_tools():
    exchange = json.loads((ROOT / "fixtures/contracts/saved_exchange.json").read_text())
    return FetchTools(FakeBackend([exchange])), exchange["recipient_id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--demo", action="store_true", help="Run both fixture prompts offline.")
    modes.add_argument("--serve-synthetic", action="store_true", help="Publish only fictional demo data.")
    args = parser.parse_args()
    tools, recipient = demo_tools()
    if args.demo:
        fixture = json.loads((ROOT / "fixtures/contracts/fetch_requests.json").read_text())
        for operation in ("lookup", "feedback"):
            print(json.dumps(tools.handle_chat(fixture[operation]["prompt"],
                             authenticated_recipient_id=recipient, command_id=operation), indent=2))
        return
    from dotenv import load_dotenv
    from uagents import Agent

    load_dotenv(ROOT / ".env")
    for name in ("FETCH_AGENT_NAME", "FETCH_AGENT_SEED"):
        if not os.getenv(name, "").strip():
            parser.error(f"Set {name} in .env first.")
    runtime = ROOT / "local-data/fetch-tools"
    runtime.mkdir(parents=True, exist_ok=True)
    os.chdir(runtime)
    agent = Agent(name=os.environ["FETCH_AGENT_NAME"], seed=os.environ["FETCH_AGENT_SEED"],
                  port=8001, mailbox=True, publish_agent_details=True)
    # Every public sender shares this fictional recipient. This is NOT app authentication.
    agent.include(make_protocol(tools, lambda sender: recipient), publish_manifest=True)
    print("Synthetic-only demo: feedback and replay receipts last until this process stops.")
    agent.run()


if __name__ == "__main__":
    main()
