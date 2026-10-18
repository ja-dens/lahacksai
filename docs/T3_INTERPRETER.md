# T3 multimodal interpreter

The standalone T3 implementation is preserved in PR #15 and assembled with T2/T4/T5 in PR #14. PR #14 ports the core to Python while preserving its raw-candidate and composed-result interfaces; PR #15 retains the original component checkpoint. Compilation/fixture tests do not establish live model accuracy. Main remains unmerged.

## Setup and verification

Use Python 3.13 (tested with 3.13.15). Dependencies are isolated in requirements-t3.txt and the resolved requirements-t3.lock rather than replacing another teammate's shared dependency files. The tracked .env.example uses GEMINI_API_KEY and keeps the context default at 25.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-t3.lock
.venv/bin/python -m unittest discover -s tests -p 'test_interpreter.py'
.venv/bin/python -m compileall -q src
.venv/bin/python scripts/check_contract_fixtures.py
```

The interpreter tests use synthetic fixtures, injected clients and the Google Gen AI SDK with httpx.MockTransport. Direct socket connections are blocked in the in-process tests. The HTTP-looking log lines from SDK transport tests describe mocked requests; they are not paid API calls. No Photon, database, API credentials or T1/T4 implementation is needed.

## Run the offline component

```sh
.venv/bin/python -m src.adapters.vision --case single
.venv/bin/python -m src.adapters.vision --case compatible
.venv/bin/python -m src.adapters.vision --case opposing
.venv/bin/python -m src.adapters.vision --case unrankable
.venv/bin/python -m src.adapters.vision --case unsupported
```

The default mode is fixture. It validates the image/record and returns a fixed candidate example through the real Python policy. It does not interpret the image. JSON explicitly reports interpretation_is_fixed_fixture=true and network_delivery_performed=false. A compatible pair retains the second meaning; an opposing pair retains the first meaning and caveat; an unrankable opposing pair abstains with unsupported status and no meaning/alternative.

## Opt-in live smoke test

Configure an API key and a model available to your API project that supports both image input and structured outputs. No model is guessed or automatically selected. A ChatGPT login is not an API key. The module reads environment variables; it does not automatically load .env files.

```sh
export GEMINI_API_KEY='your-local-api-key'
export VISION_MODEL='gemini-3.5-flash-lite'
.venv/bin/python -m src.adapters.vision --mode live
```

`GOOGLE_API_KEY` and `VISION_API_KEY` are supported aliases when GEMINI_API_KEY is absent. `--model` overrides VISION_MODEL, and `--request path/to/request.json` selects another authorized frozen v2 request. The built-in default is the synthetic shared fixture. Missing model/key returns status=unverified and exit code 2 before any SDK request. Operational or input failure returns exit code 1 with a safe error category and no fabricated interpretation. Success returns exit code 0. A configured live command makes one model request and may incur provider charges; it performs no phone send.

This branch's live model access, semantic accuracy, multilingual quality, latency and cost remain unverified. T5 verifies live operation; T6 measures semantic judgments and comprehension. Fixture/policy success is not an accuracy score.

## Integration boundary

The Python public operation accepts a frozen InterpretationRequest and a callable provider:

```python
from src.interpreter import interpret_sticker
from src.adapters.vision import GeminiVision

vision = GeminiVision(model="gemini-3.5-flash-lite")
try:
    result = interpret_sticker(saved_request, vision)
finally:
    vision.close()
```

`GeminiVision(request)` returns a validated **raw candidate object**, retaining compatibility with the earlier coordinator that calls apply_policy itself. `interpret_sticker(request, vision)` composes that adapter with policy and returns InterpretationResult. Use one of these integration patterns; do not apply the policy twice. A replacement vendor adapter implements the same callable raw-candidate boundary, honors one-call/no-retry behavior and uses prepare_request for the model-evidence projection. The Gemini client is created with one attempt and the selected timeout. Injected clients are used as given and must expose `models.generate_content`.

The caller persists its immutable request before invocation and records a failed run when an exception is raised. T3 never mutates that request or writes a result on an operational failure; it does not implement T4's database, snapshot creation, retry ledger or private delivery. VisionError exposes a safe code. Input/policy contract violations raise ValueError. Do not log provider response bodies, request content or credentials when recording errors.

## Evidence and policy

src/interpreter.py owns request validation, an explicit model-evidence projection, the structured-output schema, strict candidate validation, the output policy and composition. src/adapters/vision.py owns SDK serialization, local PNG decoding, operational response handling and the CLI. prompts/sticker.txt separates image/chat evidence, limited relationship context and presentation settings. Source metadata records provider/model and the prompt hash.

- Preserve the supplied 20–25 count bound, at most 4,000 characters per message/target and up to 24,000 recent-text characters. Reject oversized or inconsistent input rather than silently selecting a different window. Context remains chronological, preceding the target, with no age cutoff. Arrival identity/authorization and selection remain T4 responsibilities.
- The model receives the actual target PNG, target text, allowed recent-message fields, declared preferences/relationship and provenance. Unknown root/nested keys are projected out. Private destination, recipient routing ID, conversation/platform bookkeeping, stored feedback, historical summaries, archives and interpreter bookkeeping are not forwarded. Speaker IDs remain necessary evidence; these checks do not establish provider data retention or end-to-end privacy.
- Validate base64, a matching SHA-256, PNG signature, byte count, CRC/decoding and static-image support before an SDK call. The implementation supports static PNG up to 5,000,000 bytes and 16,777,216 pixels. The pixel limit is a reversible engineering safeguard. APNG animation and other formats are explicitly unsupported; there is no silent conversion or fabricated inference.
- Use one stateless Responses request with the image data URL and strict JSON schema. SDK retries are disabled. There is no previous_response_id, conversation state, tool call, repair request, feedback retrieval or second personalization call.
- Validate exact output keys, types, character bounds, normalized duplicate candidates, relation/count/rankability consistency and pair caveats before any unsupported fallback. Reject invalid JSON, duplicate JSON keys, nonfinite values, invalid schema and extra routing fields. No malformed output is disguised as an interpretation.
- Compatible pairs can show both meanings. Opposing pairs show only a rankable best meaning with uncertainty; unrankable opposing pairs abstain. The strongest two supplied candidates are used; policy never invents a weaker third candidate. Semantic compatibility, ranking and language correctness still require T6 evaluation.
- Refusal, incomplete/empty output, timeout, authentication, rate limiting, connection/API errors and invalid output remain operational failures. Unsupported semantic evidence is a valid unsupported result. Meaning is empty for that status, matching the shared fixture; T4/delivery owns the user-facing fallback wording.

## Requirement evidence

| T3 requirement | Evidence |
| --- | --- |
| One multimodal request with the real image and separate bounded/user context | AdapterTests.test_composed_service_sends_one_image_and_all_allowed_context_then_returns_policy_result; SDKTransportTests |
| Compatible/opposing/unrankable/unsupported policy | PolicyTests and all five fixture CLI cases |
| No live feedback/archive/routing leakage | EvidenceTests.test_extraneous_history_feedback_routing_and_nested_preferences_are_not_forwarded; serialized-payload inspection |
| Invalid schema/JSON, duplicate fields/candidates, errors and timeouts | PolicyTests, AdapterTests, SDKTransportTests; failure preserves input and makes no repair request |
| Unreadable/oversized/animated/dimension-limited media | MediaTests; invalid media causes zero SDK requests |
| Model setup, replaceable client, opt-in live command | Configuration/CLI tests and the commands above |
| Frozen request retained for caller error recording | No mutation on success or failure; T4 owns persistence |
| Independent completion | All 34 tests and Python compilation run without the other modules or credentials |

The integrated implementation uses Python throughout. The former source-share checkpoint is retained as historical evidence in T3_VERIFICATION.json; there is no language quota or Jac runtime dependency. See [PYTHON_MIGRATION.md](PYTHON_MIGRATION.md).

Implementation follows the Gemini API documentation for [image input](https://ai.google.dev/gemini-api/docs/image-understanding) and [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), checked October 18, 2026. The tested SDK is google-genai 2.31.0 and the default model is `gemini-3.5-flash-lite`. Detailed incident history is in [T3_ERROR_LOG.md](T3_ERROR_LOG.md).
