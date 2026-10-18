# Demo runbook

## Local page

This serves the same offline coordinator on this machine as an iMessage-style
thread. You can type as yourself or as your grandchild. Sending the laughing
sticker opens a popup with the private explanation.

```sh
.venv/bin/python -m src demo --local
```

Open the printed `http://127.0.0.1` address. The thread starts with the saved
family-chat lines. Type in the box and press send. Switch **Texting as** to
**Grandchild**, open the sticker button, and send the laughing face. The popup
says what that sticker means and that only you see the note. The five buttons
choose which saved explanation the next sticker uses: one meaning, a compatible
pair, an opposing pair, abstain, or the direct-thread wording. The page makes
no OpenAI or Photon request, and it does not show phone receipt.

## Your own Messages app

This path watches the Messages app on this Mac. When anyone sends a sticker in
any chat, including a group and a sticker you send, a popup explains why and
shows another sticker from the same pack when this Mac already has one.
Nothing is posted back into the chat. It makes one OpenAI call per sticker,
using the sticker image and up to 25 earlier messages from that chat. People
in those chats need to agree to that first.

Setup, once:

1. System Settings > Privacy & Security > Full Disk Access: turn on Cursor (or
   the terminal app you use), then quit and reopen it. macOS blocks reading
   `~/Library/Messages/chat.db` without this.
2. Make sure `.env` has a working `OPENAI_API_KEY` with credit and
   `VISION_MODEL`.
3. Check access:

```sh
.venv/bin/python -m src imessage --check
```

Run it for every Messages chat:

```sh
.venv/bin/python -m src imessage
```

To watch only one friend, pass their phone number or email as Messages knows
them:

```sh
.venv/bin/python -m src imessage --contact "+15551234567" --relationship friend
```

The popup window opens at `http://127.0.0.1:8766`. Text in any Messages chat.
When a sticker is sent, the popup shows the sticker, what it probably means,
why, and another sticker from that same pack if one is already on this Mac.
With `--contact`, only that person's one-to-one chat is watched; add
`--include-mine` to also explain stickers you send there. Add
`--include-photos` to treat photos as stickers. Only stickers that arrive
after the watcher starts are explained, and each sticker is explained once.
Press Ctrl+C to stop.

If OpenAI fails (for example, the account is out of credit), the window says
so instead of guessing a meaning.

## Offline backup demo

This path uses real coordinator, persistence, policy, routing, and transport
boundaries with synthetic provider I/O and fixed candidates. It makes no
network or model request.

```sh
.venv/bin/python -m src demo --db local-data/demo.sqlite3 --replay
.venv/bin/python -m src inspect --db local-data/demo.sqlite3 --window-id 1
.venv/bin/python scripts/evaluate_stickers.py --mode fixture \
  --output local-data/evaluation-fixture.json
```

Expected evidence:

- one accepted synthetic delivery;
- replay does not create a second send;
- the saved request has at most 25 preceding messages and no feedback;
- the evaluation report says `fixture_output_is_model_accuracy: false`.

## Live direct-space demo

1. Complete [local setup](SETUP.md).
2. Run `.venv/bin/python -m src live`.
3. From the exact `PHOTON_ALLOWED_SENDER`, open the assigned shared-line thread.
4. Use the photo button to send a static test image. Do not use the sticker
   drawer for this beta fallback.
5. Observe one explanation in the same direct thread.
6. Read SQLite evidence without exposing message text:
   - `live_receipts` has one source message receipt;
   - `live_attachments` records MIME, size, and digest;
   - `live_model_calls` records status, latency, and token counts when returned;
   - `live_delivery_status` records the provider's latest state.

Record separately:

- Photon attachment observed;
- one model call observed;
- provider accepted/dispatched/delivered;
- explanation visually received on the phone;
- end-to-end latency;
- any mismatch or retry.

Provider `delivered` is not, by itself, visual phone receipt. Never include
credentials, personal message text, phone numbers, prompts, or image bytes in a
published report.
