# T2: Photon 2.0 adapter

This module completes the independently testable T2 transport boundary. It does not establish a verified Photon line, native sticker marker, event subscription, phone receipt, or working end-to-end application. T1 supplies observed provider evidence; T4 owns persistent context/enrollment/outbox/deduplication; T5 wires authenticated ingress and real clients. No database, model or coordinator implementation is imported by T2.

## Reminder: when the Photon API key is available

**Adding the key is configuration; completing the live integration also requires the verified event hooks and real receive/send tests below.** The HTTP client accepts an API key already, but has only been tested with fake transports. Real payloads may require adapter corrections; their scope is not known until tested.

- [ ] **T1:** Confirm Photon 2.0 beta project access, required permissions, a usable channel/line and authorized test participants.
- [ ] **T5:** Load credentials outside tracked files and inject the key, project, platform and agent identities. This module does not automatically load a `.env` file; never put a real key in code, fixtures or logs.
- [ ] **T1 → T2:** Collect a sanitized real event for the selected API version. Verify the envelope, message IDs/timestamps, native sticker marker, attachment metadata and actual media access. An ordinary image must not be guessed to be a sticker.
- [ ] **T2/T5:** Supply the real `verify_event`, `decode_event` and `classify_attachment` implementations. The synthetic test signature, envelope and `metadata.demo.kind` marker are not production implementations.
- [ ] **T4/T5:** Bind `resolve_destination` to verified enrollment, source membership and the recipient's private direct space. Do not derive the destination from model output or default to the source group.
- [ ] **T1/T5:** Receive an actual supported sticker and send a fixed explanation privately. Record API acceptance and observed phone receipt separately; also verify replay/retry behavior using the original idempotency key before wiring the full automatic flow.
- [ ] **T2:** Correct any observed API/media differences, add sanitized regression examples and rerun the standalone checks. Preserve v2 boundaries or coordinate changes through T0. Record dated results, remaining blockers and actual errors in the [T2 log](errors/T2_PHOTON_ADAPTER.md), existing ERROR_LOG.md and PLANS.md.

Keep the offline mocks for repeatable tests after live access is configured. A passing mock suite does not complete this checklist; T1/T5 still own live integration evidence.

## Run the standalone checks

From the repository root, with Python 3.10 or newer:

```sh
python3 -S -m unittest discover -s tests -p 'test_photon.py'
python3 -S scripts/check_contract_fixtures.py
python3 -S -m unittest discover -s checks -p 'test_contract_fixtures.py'
```

`-S` disables installed site packages. T2 needs only Python's standard library; its tests forbid socket creation and use synthetic events, a fake coordinator, a fake enrollment resolver and fake provider/HTTP clients. The suite loads the adapter file directly so a later Jac application package initializer does not become a hidden test dependency; a subprocess regression forbids other application imports and network. No environment file is loaded, no key is read and no message is sent. The dedicated PR workflow runs these checks without write permissions.

## API and dependency injection

`src/adapters/photon.py` provides:

- `PhotonAdapter(...).normalize_message(message)` returns `NormalizedMessage(event, warning)`, containing an IncomingMessage v2 dictionary or `event=None` for an ignored event. This is a low-level mapping operation; its caller must already have authenticated the input.
- `receive_webhook(raw_body, headers, on_message)` authenticates exact raw bytes first, decodes the event with the injected decoder, normalizes the message, and calls the injected coordinator once. It returns an `IngressReceipt`; it does not supply an HTTP server or decide your server's response code.
- `send_private_explanation(delivery)` validates the four-field DeliveryRequest, resolves the trusted destination, sends via the injected client, and returns a `SendReceipt` with acceptance/error information. It never selects destinations from model output.
- `PhotonHTTPClient(project_id=..., api_key=..., transport=...)` implements beta attachment metadata/download and text-send endpoints. `transport` is injectable. Its default `urllib_transport` performs real HTTPS only when explicitly called; constructing or importing the client does not make a request.

Required adapter injections:

| Input | Required behavior |
| --- | --- |
| project_id, platform, assistant_ids | Match the configured Photon project/channel and this application's agent identities. Source IDs remain opaque. |
| client | Implements `fetch_attachment(id, max_bytes=..., timeout=...) -> Attachment` and `send_message(body, idempotency_key=..., timeout=...) -> Mapping`. Can be the supplied HTTP client, an SDK bridge or a fake. |
| verify_event(raw_bytes, headers) | Return literal True only for a valid authenticated event for the configured delivery mechanism/version. Reject failures, stale/replayed signatures as appropriate, and missing signatures. A missing callback, exception or truthy non-boolean does not authorize processing. |
| decode_event(envelope) | Extract one Message resource from the exact subscribed beta event schema, or return None for unrelated events. Select and validate the actual event type/API version before integration. |
| resolve_destination(delivery) | Read trusted enrollment and membership records; return a verified PrivateDestination bound to this recipient and source conversation, or deny access. Never parse explanation text to choose a destination. |
| classify_attachment(message, part) | Return sticker/image/audio/other from a verified native marker or explicitly supported test mode. The default returns other and never guesses that every image is a sticker. |
| timeout | Positive finite timeout in seconds, default 10, applied to each provider operation. No automatic retries occur. |

The module deliberately requires external authentication and decoder logic. Public event schemas depend on the selected webhook API version; a public agent address, a project ID or an unverified header is not sufficient authentication. The synthetic test decoder, signature header and `metadata.demo.kind` classifier are **test-only**; they are not a claim about Photon's beta wire format. Do not deploy them as real authentication/classification.

## Verified documentation mapping versus live evidence

The adapter uses **Photon 2.0 Beta**, not Spectrum, Photon Engine or Photon Health. Official sources inspected October 17, 2026:

- [Beta API specification, pinned source revision](https://github.com/photon-hq/api/blob/4c5dcaf4b106f79b92b79734e562e47cad0d7f4d/openapi/openapi.json).
- [Beta iMessage walkthrough](https://photon.codes/docs/beta/get-started/imessage): Message resource identities, received status and plain-text sends. Its reply example reuses a source space; this product instead uses an explicitly resolved private destination.
- [Beta event delivery](https://photon.codes/docs/beta/websocket/events): public events and separate replay metadata; receipt alone does not acknowledge processing.
- [Photon 2.0 introduction](https://photon.codes/blog/introducing-photon-2.0): asynchronous request acceptance versus delivery.

| Beta Message field | IncomingMessage v2 | Notes |
| --- | --- | --- |
| platform, space.id, id, sentBy.id | platform, conversation_id, message_id, sender_id | Project/platform must also match nested sender/space records. |
| status=received; configured agent IDs | from_assistant=false | Outbound status or own-agent echoes are ignored. |
| timestamps.receivedAt | sent_at | Authoritative provider observation time, normalized to timezone-aware UTC. It is not necessarily the human sender's original clock time. No age cutoff or reordering is introduced here. |
| content.type=text and content.text | kind=text, text | Ordinary text goes to history, with no interpretation trigger. |
| content.type=group and parts | accompanying text plus one source message | Text parts join in source order. Multiple attachments are not split into invented message IDs. |
| parentMessageId | reply_to_message_id | Preserved as a reference; does not pull an outside-window reply into context. |
| attachmentId plus verified classifier | kind=sticker/image/audio/other | No native beta sticker discriminator has been observed by T1; the classifier remains an integration requirement. |
| downloaded bytes | Media.data_base64, mime_type, sha256 | Compute the digest from actual bytes; ignore source-provided hashes. |

Initial sticker support is static PNG, at most 5,000,000 bytes. The HTTP client checks declared size/type/scope before download and actual bytes/Content-Type afterward. The normalizer checks PNG chunk framing/CRCs and rejects APNG. It does not decode pixels or guarantee that every structurally valid image can be interpreted. Prior photos/audio/unknown attachments are identified without downloading or interpreting them. The webhook input cap is a separate adapter default of 1,000,000 bytes; T5's server must cap its own request-body read before calling this module.

The HTTP client calls only the fixed `https://api.photon.codes/v1/projects/{project}` origin:

- GET `/attachments/{attachmentId}` for metadata, then GET `/attachments/{attachmentId}/content` for bounded bytes, requiring HTTP 200.
- POST `/messages` with `{spaceId, senderId, content: {type: text, format: plain, text}}`, requiring HTTP 202 and matching project/space/sender in the acknowledgment.

The client uses bearer auth, validates response sizes, refuses redirects that could forward credentials, has explicit timeouts, and returns safe error codes without provider response bodies. API credentials are explicit constructor inputs from T5's configuration loader. This change adds no dependency or shared `.env` fields; existing placeholder configuration remains coordinated by T0.

## Ingress behavior and failure handoff

A forwarded record has exactly the shared v2 IncomingMessage fields. The receipt's `trigger` is `interpret_sticker` for a classified sticker or `history_only` for other messages. The coordinator still enforces enabled enrollment, membership, snapshot creation and deduplication; this receipt does not grant permission to interpret or send anything.

| Case | Adapter result / caller action |
| --- | --- |
| Valid text | Forward to history only. |
| Valid classified PNG sticker | Forward actual image and preserved source identity for automatic processing. |
| Permanent unavailable/unsupported media, malformed PNG, APNG, excessive size or multiple attachments | Forward kind=sticker with sticker=null plus an explicit warning; T4's unsupported-media path supplies an honest explanation without calling the vision model. |
| Transient media timeout/network/provider failure | Error with retryable=true; do not freeze an empty image as a final snapshot. T5 may retry the original source event. |
| Bad event auth, source/media scope or credentials | Reject with safe error code; do not forward to the coordinator. Fix configuration/authorization rather than reporting successful interpretation. |
| Coordinator failure | Safe retryable coordinator_failed; do not mark processing successful or advance a delivery cursor. |
| Duplicate delivery | Preserve native message identity and forward to the coordinator's persistent ledger. No second transport-owned dedup database is introduced. |
| Same image in a distinct message | Forward independently with the new source message ID. |

An `IngressReceipt` is an application result, not an HTTP webhook acknowledgment. T5 maps it to the selected transport's success/retry policy and saves cursors only after coordinator success. It must not acknowledge a failed operation as completed. Signed event identity/signature replay handling belongs to the verified delivery verifier; source-event deduplication belongs to T4.

## Private sending and retries

DeliveryRequest has only recipient_id, source_conversation_id, source_message_id and text. Extra fields such as destination, senderId, spaceId or model commands are rejected. The resolver binds the request to an authorized source/recipient, a verified direct space, this application's agent, and exactly the agent/recipient native participants. A group or extra participant is rejected. No fallback chooses the source group or an arbitrary handle; source-chat reply IDs are not attached to a different private space.

A stable idempotency key is derived from project, platform, source conversation, source message and recipient. It is passed in Photon's required idempotency-key header. Retries reuse the original identity/key; changing the text/destination under that key may cause a provider conflict and must not be hidden by generating a fresh key. Two distinct sticker messages get distinct keys, even if the image bytes match.

There is no automatic send retry or delivered-state mutation here. T4/T5 keep the persistent outbox and interpret receipts. Timeouts may occur after provider acceptance; treat the outcome as unknown, preserve the key, and reconcile/retry explicitly. Provider idempotency does not establish application-wide exactly-once delivery or indefinite deduplication.

`status=accepted` means the provider acknowledged the operation. `delivered=false` in SendReceipt means **phone receipt was not verified by this module**, including when the provider status string says delivered. It does not assert that the recipient definitely did not receive it. T5 records actual phone/receipt evidence separately.

## Examples and completion evidence

[examples/T2_PHOTON_ADAPTER.json](examples/T2_PHOTON_ADAPTER.json) contains a synthetic provider Message, the complete normalized v2 input with actual original PNG data, the shared DeliveryRequest, actual fake-client send body and receipt. Its event decoder/metadata labels are explicitly provisional. These outputs were generated through this adapter with fake clients; they are not captured personal chats or live Photon results.

60 T2 tests cover auth/tampering, source scope, text/sticker/photo/audio handling, timestamps/replies, grouped content, bounded media and APNG, transient failures, private binding, malicious destination fields, retry conflicts, idempotency, HTTP paths/statuses/scope, redaction and redirect rejection. The 10 shared-contract regression tests and contract checker also pass. T2's dedicated [error log](errors/T2_PHOTON_ADAPTER.md) records actual discoveries and corrections; the main ERROR_LOG.md links the same incidents.

T1's existing [access report](https://github.com/ja-dens/lahacksai/issues/2#issuecomment-6242039867) has not established native sticker media or private sending. No real key, account, phone or paid plan was used for T2. Live channel checks remain separate acceptance evidence in T1/T5.

## Source ownership and Jac accounting

This is a Python vendor-transport boundary, as assigned in T2. It does not move context, interpretation policy, enrollment storage, coordinator or delivery-policy ownership out of Jac. This branch contains no Jac application source yet; report its standalone source share as 0%, not the percentage of the unrelated unpublished local prototype. The whole project's at-least-40% Jac requirement must be measured again when the Jac core owners' implementations are integrated. No filler Jac or copied teammate implementation is added to inflate this module's ratio.
