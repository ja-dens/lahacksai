# T5 mock integration and later live handoff

> Integration update: PR #14 now includes real-component bridges, a durable SQLite store and `python -m src demo`, alongside the unchanged `mock-demo` harness described below. See [CONTEXT_STORE.md](CONTEXT_STORE.md) and [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md). Live Photon sticker access and phone receipt remain unverified. Main must remain unmerged until the user requests it.

This chat/branch owns T5 assembly. This milestone is an offline harness over injected T2/T3/T4 doubles. It does not close [T5 / #6](https://github.com/ja-dens/lahacksai/issues/6): live Photon, actual multimodal inference, durable storage and verified phone receipt remain pending. The user will notify this chat when working component versions are ready. Do not merge this PR into main without that later direction.

## Reproduce the mock milestone

Tested with Python 3.13. The mock harness and real SQLite store use only the standard library. The retained requirements-t5.txt is an empty compatibility entry point; no model/Photon SDK or compiler is installed. Install from the branch:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-t5.txt
.venv/bin/python -m unittest discover -s tests -p 'test_integration.py' -v
.venv/bin/python -m compileall -q src
.venv/bin/python -m src mock-demo --replay
```

On Windows use the corresponding .venv/Scripts executables. The harness does not read .env, construct live clients or offer a live mode. CONTEXT_MESSAGE_LIMIT and EXPLANATION_LANGUAGE may be passed explicitly through the process environment to the CLI. The message limit must be 20–25; 25 is the default. Language is a fallback preference, not an override of an explicitly declared recipient profile. All image bytes, conversations and profiles are synthetic. Socket creation is denied in the integration tests.

Useful fault/policy demonstrations:

```sh
.venv/bin/python -m src mock-demo --case compatible
.venv/bin/python -m src mock-demo --case opposing
.venv/bin/python -m src mock-demo --case unsupported
.venv/bin/python -m src mock-demo --fail model --retry
.venv/bin/python -m src mock-demo --fail send-rejected --retry
.venv/bin/python -m src mock-demo --fail send-unknown --retry
```

Every output labels its mode, mock call counts, and unverified phone delivery. `accepted` means a synthetic provider acknowledgment, never real receipt. The fake store retains data only while its Python object is kept; restarting the CLI discards it. Real SQLite persistence, crash recovery, immutable database records and provider idempotency are T4/T2 properties still to integrate. The fixed interpreter does not inspect the image, infer tone or evaluate accuracy; it returns saved final v2 result examples from T3's boundary.

## Assembly-owned internal ports

The v2 IncomingMessage/InterpretationRequest/InterpretationResult/DeliveryRequest fields in CONTRACTS.md remain unchanged. The methods below are **T5's provisional injected ports**, not additional requirements imposed on teammates' APIs. When working T2/T3/T4 versions arrive, T5 will adapt them behind these ports rather than rename shared fields or force owners to rewrite their modules.

| Component | T5 port | Required behavior and ownership |
| --- | --- | --- |
| T2 ingress | Call process_event(pipeline, normalized_event, authenticated=True) after a trusted verifier succeeds | The boolean is out of band, never copied from an arbitrary payload. The demo supplies a test identity; it performs no authentication. A live entry point still needs webhook verification. |
| T4 scheduling | observe(event, settings) → window IDs | Save observed text; for an enabled sticker freeze a separate request per recipient. Replay returns the existing IDs. A changed body under an existing source identity is rejected. T4 owns exact ordering/retention and persistent atomic scheduling. |
| T4 saved work | load_job(window_id) → detached record | Fields: window_id, request, request_sha256, state, result or null, idempotency_key. This job envelope is internal metadata, not a new model-input schema. |
| T4 routing | resolve_route(window_id) → trusted enrollment | platform, conversation_id, recipient_id, destination, enabled and members. Check sender/recipient membership and reject a group destination. Re-resolve before sending to notice revoked enrollment. Real membership/destination verification is still required. |
| T4 claims | claim(window_id, phase) → boolean | Atomically claim interpreting or sending, or return false. The fake only models sequential/reentrant behavior; it provides no concurrent-worker or distributed guarantee. |
| T4 state | save_result, mark_failure, mark_accepted | Persist output separately from the frozen input. Store safe error categories and minimal acknowledgment IDs. State must survive a real process restart before a live recovery claim. |
| T3 interpreter | interpreter(frozen_request_copy) → final v2 result | One invocation on the initial supported-sticker attempt, per recipient. The T3 bridge supplies candidate policy and schema validation; T5 rejects unsafe final shapes/recipient fields as a boundary check. |
| T2 send | send_private(delivery_request, trusted_route, idempotency_key) → receipt | Internal route/idempotency arguments stay outside v2/model input. Receipt status accepted requires provider_message_id; rejected means definitively not accepted. Unclear outcomes must not be classified rejected. |

`create_pipeline(...)` accepts these objects and validated settings. `process_event(...)` triggers automatically; ordinary text is history-only and assistant echoes are ignored. `run_window(..., retry=True)` is an explicit operator/test retry, not a recipient requirement or an automatic loop. No Fetch call or feedback retrieval enters this path.

The coordinator checks request hashes, message/count/text bounds, time ordering and no age cutoff; it forwards declared preference/relationship records separately and rejects live feedback fields. T4 still must prove actual history selection, source scoping, truncation and durable immutability against its database; exercising an emulated store is not that proof. PNG signature/hash/size checks gate this prototype's media, but do not establish complete image decoding or all native sticker formats. Unsupported media uses the documented temporary English abstention without a model call.

## Failures, replays and recovery

| Saved state | Coordinator behavior |
| --- | --- |
| pending | Validate the saved request/enrollment and claim one interpretation attempt. |
| interpreted | Reuse the stored result, recheck routing, and claim a send. |
| accepted | Ignore source replays; make no additional model or send call. Phone receipt remains unverified. |
| interpretation_failed | A source replay does not retry. Explicit retry uses exactly the original saved request; this can make another model call and may incur cost with a future live client. |
| send_failed | Only a definitive rejection is retryable. Explicit retry reuses the result and stable idempotency key; it makes no extra model call. |
| blocked | No send. Fix/re-authorize the condition and explicitly retry; reuse a previously saved valid result. |
| interpreting | Interrupted/in-progress claim: stop for reconciliation. Never silently duplicate a possible billed request. |
| sending / delivery_unknown | A send may already have succeeded. Replays and retry=True stop for reconciliation; no blind resend. A verified lookup/receipt recovery mechanism remains a future T2/T4 integration task. |

A simulated crash after fake provider acceptance tests that a **retained fake store** prevents a repeat send on coordinator reconstruction. It is not a claim about an actual database/process crash. There is no exactly-once guarantee across independent workers. Real store transactions, account-bound authorization, webhook replay handling and provider acknowledgment reconciliation must be verified when components arrive.

## Evidence before enabling a live path

- Obtain the actual T2/T3/T4 source commits and runnable commands supplied by the user. Write small bridges in T5-owned files and run their component tests plus this suite against the real implementations.
- T1 must demonstrate the chosen beta channel/line, usable sticker bytes, source identities, and private sending. Its earlier access-blocker report is not a passing test.
- Configure one authorized image-capable model API with budget and a permitted test exchange. Measure actual inference behavior and one-call routing; mock outputs provide no accuracy, token-cost or latency result.
- Bind test users/source chats/private destinations through verified enrollment. Confirm paused chats, multiple recipients and revoked access with actual membership checks.
- Exercise durable snapshots and replay/recovery using real T4 storage and T2 acknowledgment/idempotency semantics. Resolve unknown outcomes before sending again.
- Observe an actual phone explanation, record how receipt was verified, and distinguish it from API acceptance. Document permissions, deletion/retention, deployment and remaining limits.

T6 evaluation, T7 packaging and optional T8 do not block this mock milestone. Continue this chat for later T5 work; append actual incidents to [T5_ERROR_LOG.md](../T5_ERROR_LOG.md) and [ERROR_LOG.md](../ERROR_LOG.md).
