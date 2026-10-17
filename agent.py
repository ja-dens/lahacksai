"""Sponsor mailbox quickstart: https://uagents.fetch.ai/docs/examples/asi-1.

This example answers questions about the sun. Sticker/Photon logic comes later.
"""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

ROOT = Path(__file__).resolve().parent
SUBJECT = "the sun"
protocol = Protocol(spec=chat_protocol_spec)
client = None


def reply_message(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")],
    )


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id
        ),
    )
    text = "".join(item.text for item in msg.content if isinstance(item, TextContent))
    response = "I could not answer that right now. Please try again."
    if not text.strip():
        response = "This quickstart accepts text. Try asking a question about the sun."
    else:
        try:
            result = client.chat.completions.create(
                model="asi1",
                messages=[
                    {"role": "system", "content": (
                        f"You are a helpful assistant who only answers questions about {SUBJECT}. "
                        "For other topics, politely say that you do not know about them."
                    )},
                    {"role": "user", "content": text},
                ],
                max_tokens=2048,
            )
            response = result.choices[0].message.content or response
        except Exception as exc:
            ctx.logger.error(f"ASI:One request failed ({type(exc).__name__}).")
    await ctx.send(sender, reply_message(response))


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


def main():
    global client
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check imports and ACP schema offline.")
    args = parser.parse_args()
    if args.check:
        ChatMessage.model_validate_json(reply_message("setup check").model_dump_json())
        print(f"Offline check passed: uagents {version('uagents')}, openai {version('openai')}.")
        return

    load_dotenv(ROOT / ".env")
    for name in ("ASI1_API_KEY", "FETCH_AGENT_NAME", "FETCH_AGENT_SEED"):
        if not os.getenv(name, "").strip():
            parser.error(f"Set {name} in the repo's .env file first.")
    client = OpenAI(
        base_url="https://api.asi1.ai/v1",
        api_key=os.environ["ASI1_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )
    runtime = ROOT / "local-data" / "fetch"
    runtime.mkdir(parents=True, exist_ok=True)
    os.chdir(runtime)
    agent = Agent(
        name=os.environ["FETCH_AGENT_NAME"],
        seed=os.environ["FETCH_AGENT_SEED"],
        port=8001,
        mailbox=True,
        publish_agent_details=True,
    )
    agent.include(protocol, publish_manifest=True)
    agent.run()


if __name__ == "__main__":
    main()
