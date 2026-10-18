# T3 error log

This chat owns T3 on local branch codex/t3-multimodal-interpreter, based on main commit bb236d875dc080270a7e94dcaa3033511a5f07e5. Date: October 17, 2026 (America/Los_Angeles).

Record observed defects and tooling incidents here; synthetic negative tests are not new incidents. The repository-wide [ERROR_LOG.md](../ERROR_LOG.md) retains summaries. No credentials or personal chats belong in either log.

## T3-001: malformed candidate sets bypassed validation

Observed: the earlier local apply_policy accepted an empty candidate list with relation compatible and returned unsupported. An early abstention return preceded cardinality/consistency checks. Reproduced with a synthetic object, no network.

Correction: validate the complete candidate object and relation/count/rankability/caveat consistency before selecting a result. Add regression cases for empty pairs and unrankable malformed pairs.

Prevention: every fallback must be reached through validated output, never used to hide malformed model responses. Status: resolved. Verified by the 34-test T3 suite, including the specific policy, payload-projection and media regressions; all tests passed without network access.

## T3-002: unrelated request fields reached the model payload

Observed: a mock SDK captured synthetic feedback and private-destination markers in text_context. The earlier adapter copied every root request field except sticker. No actual private data or network was used.

Correction: build an explicit model-evidence projection from the v2 request and nested preferences/relationship/message fields. Keep delivery destinations, recipient routing, older history, validation records and interpreter bookkeeping outside the model payload.

Prevention: inspect the serialized SDK payload in tests, including unexpected fields nested inside user context and messages. Status: resolved. Verified by the 34-test T3 suite, including the specific policy, payload-projection and media regressions; all tests passed without network access.

## T3-003: unreadable image bytes were forwarded to the SDK

Observed: base64 of the text image, labeled image/png with a false digest, reached the mock SDK. The adapter trusted the upstream record rather than validating its own image boundary. No network was used.

Correction: verify base64, byte limit, digest and PNG signature, then decode/check a bounded static PNG with Pillow before any SDK request. Test corrupt PNG data, unsupported MIME types, animation, size and dimensions.

Prevention: independent model adapters must reject invalid media even when called without T4 normalization. Status: resolved. Verified by the 34-test T3 suite, including the specific policy, payload-projection and media regressions; all tests passed without network access.

## T3-004: Jac did not narrow types through a validation helper

Observed: the first Jac check reported 13 errors when dynamic JSON values were passed through a custom require helper. A second check exposed five remaining optional/Any references. Runtime fixture execution succeeded, but that did not satisfy static checking.

Cause: the pinned Jac type checker does not infer narrowing from the helper and retains an existing variable's inferred Any type after reassignment.

Correction: keep strict runtime guards first, then use explicit typed conversions at checked uses; annotate the optional previous timestamp. Do not coerce unvalidated values into validity. Jac check now passes. The later nullable-field review also exposed a literal-list inference conflict when reusing a field-list variable; separate typed request_fields/message_fields names resolved it.

Prevention: run Jac checks independently of a later successful shell command; use fail-fast command groups. Status: resolved and verified with jac check src --nowarn.

## T3-005: mocked CLI constructor broke class-based cleanup

Observed: the first full suite passed 31 tests but errored in the CLI failure test because replacing OpenAIVision with a mock made isinstance's second argument invalid.

Correction: cleanup checks for an actual returned provider and its callable close operation rather than inspecting the constructor symbol. The full suite now passes 34 tests, including safe-code failure output and unavailable live configuration.

Prevention: test cleanup/error paths with injected constructors and keep resource ownership independent of a patched class symbol. Status: resolved.

## Verification limits

All recorded corrections passed the standalone T3 suite and Jac check. The SDK HTTP tests use MockTransport and fake credentials, including simulated 401/429/500/timeout responses. No live image inference, phone send, model accuracy score or ASI:One call is claimed. Missing live configuration is an explicit unverified result, not an implementation failure.

## T3-006: legacy environment example contradicted the agreed window

Observed: the tracked environment example still set CONTEXT_MESSAGE_LIMIT=8, while D08 and the v2 request require 20–25 and the selected implementation default is 25. Copying that example into an integrated build would conflict with T3's validated boundary.

Correction: set the example to 25 and document OPENAI_API_KEY plus the supported VISION_API_KEY alias; no real .env or credentials were edited.

Prevention: keep shared example defaults aligned with the versioned contract and coordinate this small shared-file change at T0/T4 integration. The existing window-range tests verify rejection outside 20–25. Status: resolved by inspection and boundary tests.

## T3-007: Jac generated an unignored local cache

Observed: the first git status for the new component listed src/.jac/cache/interpreter.*.jir after runtime tests. The inherited planning repository ignored Python caches but not Jac's generated cache. No cache was committed.

Correction: add .jac/ to .gitignore and stage application source explicitly. Prevention: inspect untracked file names before staging and keep compiled artifacts out of review. Status: resolved; the cache is ignored.

## T3-008: unknown relationship provenance needed a nullable field

Observed during handoff review: concurrent T0 contract clarifications describe relationship_source as string or null, while the initial T3 helper required a string. The initial fixture always had a declared relationship and did not exercise the unknown relationship case.

Correction: accept explicit null provenance, verify a null relationship/source survives SDK serialization, and require normalized nullable keys to be present rather than rebuilding omitted snapshot fields. Two new tests cover this boundary, bringing the suite to 34 tests.

Prevention: test valid missing-value defaults alongside populated fixtures and check shared contract clarifications before handoff. Status: resolved by the full suite and Jac check. The other checkout's concurrent documentation changes were preserved.
