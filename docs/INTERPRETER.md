# One-call interpreter (#4 / T3)

`src/interpreter.jac` validates the frozen v2 context, coordinates exactly one
adapter invocation, and applies the candidate policy. `src/adapters/vision.py`
contains PNG decoding and the replaceable OpenAI Responses SDK boundary.

```sh
source .venv/bin/activate
python -m pip install -r requirements-agent-modules.txt
python -m unittest discover -s tests -p 'test_interpreter.py'
jac check src --nowarn
```

The tests use the real installed SDK with `httpx.MockTransport`. They inspect
serialized requests, including the supplied PNG bytes, and never contact a model.

## Decisions

| Decision | Reason and tradeoff |
| --- | --- |
| One image-and-context request | The model sees the actual sticker and frozen conversation together; personalization does not add a second request. |
| Keep OpenAI Responses behind an injected adapter | Matches the recorded local prototype direction, while preserving a replaceable boundary. ASI:One's chat API is a separate service and its key is not silently reused. |
| Use strict JSON schema plus Jac validation | Structured output constrains shape; Jac still checks counts, duplicate wording, rankability and the display policy. Neither proves the model's judgment is correct. |
| Select model-input fields explicitly | Recipient routing, API keys, feedback, older history and unknown extra fields are not sent. T4 owns selecting/freezing the correct conversation window. |
| Disable SDK retries | A timeout or server error stays one attempted request. Retry policy belongs to later integration. |
| Decode PNGs before inference | Corrupt, animated, oversized or hash-mismatched media fails before spending a request. This adds Pillow as an isolated dependency. |
| Retain failed-run evidence | Model errors and invalid outputs preserve the snapshot and failed status; they do not produce a fabricated meaning. |

The request's 20–25-message bound, chronological preceding order, per-message and
target text limits, recent-text budget, timezone-aware timestamps, presentation
settings and null age cutoff are checked. Old messages remain eligible; there is
no inactivity cutoff. Unknown relationships can stay null. Exact arrival-sequence
selection and conversation isolation remain T4's responsibility, because the
published `recent_messages` boundary does not carry those selection records.

The policy matches the published candidate/result fixtures:

- One ranked candidate: `interpreted`, one meaning.
- Compatible ranked pair: `ambiguous`, meaning plus alternative.
- Opposing ranked pair: `ambiguous`, strongest meaning only, with a caveat.
- No defensible candidate or unrankable candidates: `unsupported`, no meaning.

All proposed meanings require a nonempty uncertainty caveat. Extra or duplicate
candidates, mismatched relation/counts, non-boolean rankability and unexpected
output fields fail validation. Textual duplicate checks cannot detect all semantic
duplicates; compatibility, tone and accuracy need T6's held-out evaluation.

Implementation defaults: static PNG only, at most 5,000,000 decoded bytes and
16,000,000 pixels, 30-second SDK timeout, no SDK retries. Other image formats or
animations need an explicit scope change. The adapter uses `store=False` and no
conversation continuation or retrieval tools; this flag is not a general promise
about provider retention policies.

## Calling and replacing the module

```python
from src.adapters.vision import VisionAdapter

adapter = VisionAdapter(configured_openai_client, configured_vision_model)
result = adapter.interpret(frozen_request)
run = adapter.last_run
```

The input is deep-copied before use and remains unchanged. `last_run` contains the
snapshot, status, result or error type, provider/model, and prompt hash. It is an
in-memory handoff record, not a durable database write. T4/T5 must persist each
record before reuse of the adapter; one adapter instance is intended for one
in-flight request. Failures raise the original exception and leave `result=None`.
No exception message or credentials are included in the failure record.

To replace the provider, supply the same orchestration hooks (`start_run`,
`generate(snapshot, context)`, `finish_run`, `fail_run`) to
`src.interpreter.interpret_sticker`. `generate` returns the candidate dictionary;
Jac retains the validation and display policy. The current Python adapter's
`client` may also be replaced with an SDK-compatible fake for testing.

## Opt-in live smoke check

Set `VISION_API_KEY` to an authorized **OpenAI API** key and `VISION_MODEL` to an
account-accessible model supporting image inputs and structured outputs. Both
remain in ignored `.env`. No default model, account access or budget is assumed.

```sh
python -m src.adapters.vision --smoke
```

This explicit command sends the demo PNG and frozen fixture context once
and may incur API charges. A ChatGPT login or ASI:One key does not configure this
adapter. Live inference, latency, cost and accuracy have not been verified here.
T5 owns live access/integration, and T6 owns semantic evaluation.

Request structure was checked against the official [image input guide](https://developers.openai.com/api/docs/guides/images-vision)
and [structured output guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses),
then tested against the pinned openai 3.34.0 SDK serialization. These checks do
not establish live compatibility with an unconfigured model.

`requirements-agent-modules.txt` isolates the module setup from the unpublished
backend dependencies. T0 should consolidate it with that backend's reviewed
dependency configuration. `src/fetch_tools.jac` is a small additional T8 core
module so product rules remain in Jac rather than expanding the Python transport.
