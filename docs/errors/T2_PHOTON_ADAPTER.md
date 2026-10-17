# T2 chat error log — Photon adapter

Task: T2 / GitHub issue #3. Date: October 17, 2026, America/Los_Angeles. Branch: codex/t2-photon-adapter. This log is scoped to work in this chat; append new actual incidents here and summarize them in ../../ERROR_LOG.md. Hypothetical cases belong in tests/design notes rather than being presented as observed production errors.

## T2-001 — documentation entry point selected another Photon product

Observed: the generic docs.photon.codes URL redirected to Spectrum documentation, and broad searches also returned Photon Health and Photon Engine. Those are not the selected Photon 2.0 beta API.

Cause: multiple products share the name and the generic documentation landing page defaults to Stable/Spectrum.

Correction: use explicit /docs/beta/ pages and the official photon-hq/api OpenAPI source pinned to 4c5dcaf4b106f79b92b79734e562e47cad0d7f4d. Do not copy another product's webhook headers or sticker fields.

Prevention/verification: PHOTON_ADAPTER.md records the version, source revision and actual mapped resource fields. Tests assert beta message/attachment paths and required idempotency header. No live payload is claimed.

Status: resolved for the documented source mapping; native sticker/event-envelope verification remains with T1/T5.

## T2-002 — AsyncAPI schema inspection assumed the wrong layout

Observed: a read-only Ruby inspection tried components.messages and failed with KeyError. This downloaded AsyncAPI 3 document keeps message definitions under channels.

Correction: inspect the document structure first. Beta's event-schema endpoint is version-specific; do not infer a production webhook envelope from an assumed components layout. Keep event decoding injected and mark the test envelope as synthetic.

Prevention/verification: authentication precedes the injected decoder; unknown events and invalid JSON have tests. The module makes no production event-envelope claim. No repository or account mutation resulted from the inspection failure.

Status: resolved inspection failure; actual subscribed event schema remains an integration input.

## T2-003 — authorization errors could be misclassified as content/send failures

Observed during code review: the first implementation sent all non-retryable media errors through unsupported-media fallback, which included credential/scope failures. A resolver's PermissionError also became a retryable generic send failure.

Correction: allow only explicit content/unavailable-media error codes into automatic abstention. Reject authentication/scope errors without forwarding; report denied destination access as non-retryable unauthorized_destination. Validate real REST acknowledgments against the requested project/space/sender and require the documented 202 status.

Prevention/verification: regression tests reject media 401/403/cross-project scope, deny an unenrolled recipient without calling send, and reject mismatched acknowledgment scope/status. All 59 T2 tests and 10 shared-contract tests passed with network forbidden; the fixture checker passed with site packages disabled.

Status: resolved in this branch. This is local software verification, not evidence of a deployed incident or a live Photon test.

## Verified publication checkpoint

The implementation was committed as 31d52069dae9ef80c769f2959ba05bcedd1c0a89 and published for review in [PR #13](https://github.com/ja-dens/lahacksai/pull/13), on codex/t2-photon-adapter. Both remote adapter and planning checks passed. The PR remains open and unmerged; no live Photon/phone verification occurred. Future errors from work in this chat should continue here and in the existing ERROR_LOG.md.
