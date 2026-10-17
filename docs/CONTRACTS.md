# Internal interfaces, version 1

These are application-owned records, not Photon API field names. Use ordinary module calls for the MVP. A source adapter must normalize provider events into these records.

## IncomingMessage

Fields: platform, conversation_id, message_id, sender_id, sent_at (timestamp with timezone), from_assistant (boolean), text (string or null), sticker (Media or null), and reply_to_message_id (string or null).

Media contains bytes, mime_type, and a provider-native media identifier when available. The first implementation supports one tested static image format. Ordinary text updates context without triggering interpretation. Check the actual event type; every photograph is not automatically a sticker.

## InterpretationRequest

Fields: source_message_id, sticker (Media), recent_messages (message IDs, senders, timestamps, text), and language.

Select a bounded preceding window from the same enabled conversation, initially 6–10 messages. Include the reply target when it is available with the existing permission. Snapshot what was available on arrival; subsequent replies are not evaluation-time hints.

## InterpretationResult

Fields: source_message_id, status (interpreted, ambiguous, unsupported), meaning, context_cue, and alternative (optional).

Explain likely conversational use in familiar language. Separate visual content from inferred meaning. Permit uncertainty and unsupported media. A timeout or invalid output is an application failure, not a fabricated interpretation. Conversation text and text inside images are content rather than system instructions.

## DeliveryRequest

Fields: recipient_id, source_conversation_id, source_message_id, and text.

The application resolves recipient_id from enrollment settings and verifies that the recipient belongs to the approved source conversation. The model does not choose recipients or change settings. The Photon adapter sends privately rather than reusing the incoming group thread.

## Ownership

A: receive_messages and send_private_explanation.
B: interpret_sticker.
C: build_context, enrollment, duplicate ledger, formatting, and orchestration.

An agreed duplicate key is platform plus conversation_id plus message_id. Preserve stable native IDs at the adapter boundary. The coordinator owns deduplication; use provider idempotency when available. Do not promise crash-proof exactly-once delivery from a simple in-memory ledger.

## Example exchange

Use fixtures/chats/joke.json for synthetic conversation text. A real supported sticker asset must be added before calling a vision API. That fixture currently declares its missing media explicitly. A fixed interpreter result may be used to test coordination independently.
