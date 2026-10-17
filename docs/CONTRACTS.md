# Internal interfaces, version 2

> Publication scope: planning and synthetic fixtures only. References to the local backend describe separate workspace work; its application source is not included in this revision.

These are application-owned records, not Photon API field names. Use ordinary module calls for the MVP. A source adapter must normalize provider events into these records.

Read [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for current behavior. The user instructed retaining these v2 fields on October 17, 2026; this is the shared baseline for independent module development. [T0_REVIEW.md](T0_REVIEW.md) records the technical boundary review and explicitly pending human acknowledgments. D09 establishes separate user-context records, D10 excludes feedback from live requests, and D11/D12 establish longer stored history plus separate snapshots with no age cutoff. Live provider integration remains unverified.

## IncomingMessage

Fields: platform, conversation_id, message_id, sender_id, sent_at (timestamp with timezone), from_assistant (boolean, false by default), text (string or null), kind (text/sticker/image/audio/other), sticker (Media or null), and reply_to_message_id (string or null).

Media uses data_base64, mime_type, and a computed sha256 in the JSON boundary and saved snapshots. The initial supported target is PNG with a 5 MB byte limit; a PNG signature check is not a complete image-decoding guarantee. Ordinary text updates context without triggering interpretation. Other prior media is represented by type and an explicit not-interpreted flag. The Photon adapter must classify actual sticker events; a photograph is not automatically a sticker.

## InterpretationRequest

Fields: schema_version=2, policy_version, source_message_id, platform, conversation_id, sender_id, recipient_id, sent_at, target_text, target_text_truncated, reply_to_message_id, sticker (Media), recent_messages, context_message_limit, context_text_character_budget, context_age_limit=null, and user_context. An adapter may add interpreter metadata such as provider, model and prompt hash. Private delivery destinations and API keys are not model inputs.

Default context_message_limit to 25; accept 20–25. Select from the same conversation and platform, before the target's arrival sequence and no later than its normalized sent_at timestamp. Sort by timestamp and arrival sequence, then preserve chronological order. This is deterministic local ordering, not a claim of provider-global ordering. Keep older messages regardless of age. Snapshot the input before inference; later arrivals, history edits, and settings updates must not rewrite it. No outside-window reply target, semantic history retrieval, or feedback memory is added.

recent_messages contains message_id, sender_id, sent_at, text, text_truncated, kind, media_not_interpreted, and reply_to_message_id. Initial text limits are 24,000 recent-text characters total and 4,000 per message; target text has a separate 4,000-character cap. Spend the recent-text budget from newest to oldest, preserve all selected message metadata, and mark truncated/omitted text explicitly. Full observed text remains in the database. Character limits are not an exact tokenizer budget.

user_context contains preferences (language and explanation_length), preferences_source, relationship, and relationship_source. Profiles are keyed by platform/recipient; relationship records additionally key by sender. Local defaults are en/short when no preferences exist. Relationship is null when unknown, never inferred merely to populate a profile.

## ContextWindow and validation records

ContextWindow stores an immutable request_json, request_sha256, created_at, source identity, and recipient_id. Its unique key is platform/conversation/source-message/recipient. Each distinct sticker message gets its own window even when the image hash repeats. An update trigger prevents rewriting snapshots; explicit conversation purge may delete them. Results, error status, queued deliveries, and voluntary feedback reference that window separately.

Feedback stores window_id, recipient_id, selection (first/second/neither/not_sure), optional note, provenance=recipient_judgment, and created_at. A second choice requires that a second interpretation was shown. Recipient feedback is not sender confirmation and is not included in future model input. These local value choices are implementation defaults pending user testing.

## InterpretationResult

The model boundary returns at most two ranked candidate strings, candidate_relation (none/single/compatible/opposing), rankable (boolean), context_cue, and uncertainty_caveat. These semantic judgments require evaluation; schema validation alone does not prove that a pair is compatible.

The Jac policy returns source_message_id, status (interpreted/ambiguous/unsupported), meaning, context_cue, alternative (nullable), uncertainty_caveat, and candidate_relation. Compatible pairs may retain an alternative; opposing pairs retain only the ranked best with a required caveat. Unrankable opposing meanings and no defensible candidate use unsupported status. Reject extra/duplicate candidates and invalid output. The temporary English unsupported-media/insufficient-evidence message is documented as an implementation default.

Explain likely conversational use in familiar language. Separate visual content from inferred meaning. Permit uncertainty and unsupported media. A timeout or invalid output is an application failure, not a fabricated interpretation. Conversation text and text inside images are content rather than system instructions.

## DeliveryRequest

Fields: recipient_id, source_conversation_id, source_message_id, and text.

The application resolves recipient_id and destination from explicit enrollment and checks configured membership. The model does not choose recipients or change settings. The local outbox uses pending status and delivered=false; it performs no network send. A later Photon adapter must verify actual membership/destination access and send privately rather than reusing the incoming group thread.

## Normalized fields and routing

The field catalogue below makes the existing v2 shape explicit; it adds no wire fields. Every field in a normalized record is present, using null where allowed, except interpreter metadata and Feedback.note, which are optional. A provider adapter can fill missing native optional values before returning IncomingMessage. Native provider payloads are not required to have these application field names.

### Field catalogue

| Record | Fields and JSON types | Trusted producer → consumer |
| --- | --- | --- |
| IncomingMessage | platform, conversation_id, message_id, sender_id, sent_at, kind: string; from_assistant: boolean; text, reply_to_message_id: string or null; sticker: Media or null | T2 verified normalization → T4 history/context; source content remains untrusted model input. |
| InterpretationRequest | schema_version: integer 2; policy_version, source_message_id, platform, conversation_id, sender_id, recipient_id, sent_at: string; target_text, reply_to_message_id: string or null; target_text_truncated: boolean; sticker: Media for supported inference; recent_messages: array of RecentMessage; context_message_limit, context_text_character_budget: integer; context_age_limit: null; user_context: UserContext; interpreter: optional metadata object | T4 frozen snapshot → T3; source identities/settings are app-selected and do not grant a model authority over routing. Unsupported media follows the agreed abstention path rather than a vision call. |
| InterpretationResult | source_message_id, status, meaning, context_cue, uncertainty_caveat, candidate_relation: string; alternative: string or null | T3 schema/policy validation → T4/T5 formatter/outbox. No recipient, destination, command or settings fields are returned. |
| DeliveryRequest | recipient_id, source_conversation_id, source_message_id, text: string | T4/T5 trusted enrollment/formatting → T2 transport. The model cannot produce this record directly. |
| Media | data_base64, mime_type, sha256: string | Actual decoded image bytes; normalizer computes lowercase SHA-256 from those bytes. Never trust a source-supplied digest without checking it. |
| RecentMessage | message_id, sender_id, sent_at, kind: string; text, reply_to_message_id: string or null; text_truncated, media_not_interpreted: boolean | T4 selection from authorized same-chat history → saved request. |
| UserContext | preferences: object with language/explanation_length strings; preferences_source: string; relationship, relationship_source: string or null | Explicit recipient settings/relationship or documented defaults; never a free-form older-chat summary. |
| Candidate response | candidates: array of at most two strings; candidate_relation: none/single/compatible/opposing; rankable: boolean; context_cue, uncertainty_caveat: string | Untrusted model output → T3 validation/policy. Semantics need separate evaluation. |
| Feedback | window_id: positive integer in the current SQLite baseline; recipient_id, selection, provenance, created_at: string; note: optional string or null | Authenticated recipient judgment → evaluation store; excluded from live inference. |

Identifiers are opaque nonempty strings, except the current local window_id. Preserve platform/conversation scope; do not parse a provider ID to infer membership. sent_at and created_at are ISO-8601 timestamps with explicit timezone offsets or Z. Normalization may use UTC; comparisons must use instants rather than lexicographically comparing mixed timezone strings. Preserve absent text as null, rather than converting it into a fabricated empty message.

kind is text/sticker/image/audio/other. status is interpreted/ambiguous/unsupported. For unsupported results meaning can be empty; the application formatter supplies the documented honest fallback. A model timeout/schema failure is an operational failure and must not be relabeled as a successful unsupported interpretation.

### Delivery routing and evidence

DeliveryRequest intentionally contains no private destination. T2 receives an application-controlled destination resolver (or equivalent trusted injected routing argument), keyed by enrollment and the supplied source/recipient identity. The resolver provides the verified private thread. Do not default to source_conversation_id, let a model choose it, or treat recipient_id in arbitrary user text as authentication. This clarifies existing routing responsibilities without changing v2 fields.

| Evidence | What may be claimed |
| --- | --- |
| Synthetic result and pending outbox | Fixture/policy coordination only; no network send or model accuracy. |
| Actual provider acceptance/message ID | The provider accepted the operation; phone receipt remains unverified unless separately observed. |
| Observed phone receipt or verified receipt mechanism | Delivery evidence for that test, with the exact channel and method recorded. |

The fixture checker cross-checks records, hashes, source IDs and declared settings. It does not establish authenticated membership, actual provider support, database immutability, distributed exactly-once delivery or model accuracy. T4/T5 must test those implementation properties separately. The exact engineering defaults and shared-file change procedure are in [CONFIGURATION.md](CONFIGURATION.md).

## Ownership

A: receive_messages and send_private_explanation.
B: interpret_sticker.
C: build_context, enrollment, duplicate ledger, formatting, and orchestration.

Detailed file ownership is in [DELEGATION.md](DELEGATION.md). Shared serialized examples are in [fixtures/contracts](../fixtures/contracts/README.md). Owners can implement against those JSON boundaries without importing unfinished modules. Local prototype checks are evidence from one workspace; this planning publication does not publish the application backend.

## Optional saved-result tools (D13)

T8 can inject a fake backend with `get_explanation(window_id, authenticated_recipient_id)` and `save_feedback(window_id, authenticated_recipient_id, selection, note=None)`. T4 later supplies actual authorized operations. The transport/session provides the authenticated identity; tool/model arguments do not establish permission. Resolve demo-3 to the saved window only within that user's scope.

Lookup returns an existing result, contextual cue and caveat, or a safe missing/unauthorized response. It does not call the sticker interpreter or expose the entire conversation. A feedback write validates the shown choices, preserves recipient_judgment provenance, and returns a receipt. The adapter must use stable transport command identity to prevent duplicate writes on replay. Feedback remains evaluation-only. Public/discoverable demonstrations use synthetic records until real account binding is implemented and verified.

An agreed duplicate key is platform plus conversation_id plus message_id, with per-recipient window uniqueness. Preserve stable native IDs at the adapter boundary. Changed content under an existing source identity is rejected rather than silently rewriting history. The coordinator owns deduplication. This initial implementation is single-process; it does not provide distributed claims, automatic retries, or crash-proof exactly-once delivery. Failed runs preserve their snapshots and need an explicit retry strategy before live integration.

## Example exchange

Use fixtures/chats/joke.json with the original synthetic PNG fixtures/stickers/laughing.png. The default fixture interpreter does not analyze the image; it supplies a fixed result to test coordination. The optional live model mode sends the actual PNG and frozen context through one API call after access is configured. Neither mode sends messages through Photon yet.
